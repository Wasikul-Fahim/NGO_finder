from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentNgo, CurrentUser, DbSession, VerifiedNgo, require_roles
from app.api.v1.donations import resource_out
from app.core.errors import AppError, conflict, forbidden, not_found
from app.models import (
    Beneficiary,
    Campaign,
    CampaignBeneficiary,
    CampaignStatus,
    Resource,
    ResourceDistribution,
    Role,
    User,
)
from app.schemas.common import Page
from app.schemas.finance import (
    BeneficiaryEnroll,
    CampaignBeneficiaryOut,
    DistributionCreate,
    DistributionOut,
    MySupportOut,
    ResourceCreate,
    ResourceOut,
    ResourceUpdate,
    SupportUpdate,
)
from app.services import campaigns as campaign_svc
from app.services.audit import log_action
from app.services.pagination import PageParams, paginate

router = APIRouter(tags=["resources"])
BeneficiaryUser = Annotated[User, Depends(require_roles(Role.BENEFICIARY))]


def _writable_campaign(db, campaign_id: int, ngo) -> Campaign:
    campaign = campaign_svc.get_owned_campaign(db, campaign_id, ngo)
    if campaign.status == CampaignStatus.ARCHIVED:
        raise conflict("This campaign is archived and can no longer be changed.")
    return campaign


def _owned_resource(db, resource_id: int, ngo) -> Resource:
    r = db.scalar(select(Resource).options(joinedload(Resource.campaign)).where(Resource.id == resource_id))
    if r is None:
        raise not_found("Resource")
    if r.campaign.ngo_id != ngo.id:
        raise forbidden("This resource belongs to another NGO.")
    return r


def _link_out(link: CampaignBeneficiary) -> CampaignBeneficiaryOut:
    b = link.beneficiary
    return CampaignBeneficiaryOut(
        beneficiary_id=b.id, name=b.name, contact=b.contact, location=b.location,
        required_assistance=b.required_assistance, support_status=link.support_status,
    )


def _dist_out(d: ResourceDistribution) -> DistributionOut:
    return DistributionOut(
        id=d.id, resource_id=d.resource_id, resource_name=d.resource.name,
        beneficiary_id=d.beneficiary_id, beneficiary_name=d.beneficiary.name, quantity=d.quantity,
        distribution_date=d.distribution_date,
    )


# ------------------------------------------------------------------ resources

@router.post("/campaigns/{campaign_id}/resources", response_model=ResourceOut, status_code=201)
def add_resource(campaign_id: int, data: ResourceCreate, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    campaign = _writable_campaign(db, campaign_id, ngo)
    r = Resource(campaign_id=campaign.id, **data.model_dump())
    db.add(r)
    db.flush()
    log_action(db, user, "CREATE_RESOURCE", "Resource", r.id,
               {"campaign_id": campaign.id, "name": r.name, "quantity_total": r.quantity_total})
    db.commit()
    return resource_out(r)


@router.get("/campaigns/{campaign_id}/resources", response_model=list[ResourceOut])
def list_resources(campaign_id: int, ngo: CurrentNgo, db: DbSession):
    campaign_svc.get_owned_campaign(db, campaign_id, ngo)
    rows = db.scalars(select(Resource).where(Resource.campaign_id == campaign_id).order_by(Resource.id))
    return [resource_out(r) for r in rows]


@router.patch("/resources/{resource_id}", response_model=ResourceOut)
def update_resource(resource_id: int, data: ResourceUpdate, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    r = _owned_resource(db, resource_id, ngo)
    if r.campaign.status == CampaignStatus.ARCHIVED:
        raise conflict("This campaign is archived and can no longer be changed.")
    changes = data.model_dump(exclude_unset=True)
    for required in ("name", "quantity_total"):
        if required in changes and changes[required] is None:
            raise AppError(422, "VALIDATION_ERROR", "Please correct the highlighted fields.",
                           {required: "This field cannot be empty."})
    if "quantity_total" in changes and changes["quantity_total"] < r.quantity_allocated:
        raise conflict(f"{r.quantity_allocated} already distributed; total cannot be lower than that.")
    for field, value in changes.items():
        setattr(r, field, value)
    log_action(db, user, "UPDATE_RESOURCE", "Resource", r.id, {"fields": sorted(changes)})
    db.commit()
    return resource_out(r)


@router.post("/resources/{resource_id}/distributions", response_model=DistributionOut, status_code=201)
def distribute(resource_id: int, data: DistributionCreate, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    r = _owned_resource(db, resource_id, ngo)
    if r.campaign.status == CampaignStatus.ARCHIVED:
        raise conflict("This campaign is archived and can no longer be changed.")
    link = db.scalar(select(CampaignBeneficiary).where(
        CampaignBeneficiary.campaign_id == r.campaign_id,
        CampaignBeneficiary.beneficiary_id == data.beneficiary_id))
    if link is None:
        raise AppError(409, "NOT_ELIGIBLE", "That person is not enrolled in this campaign.")
    # Atomic check-and-increment: two concurrent requests can never over-allocate.
    result = db.execute(
        update(Resource)
        .where(Resource.id == r.id, Resource.quantity_allocated + data.quantity <= Resource.quantity_total)
        .values(quantity_allocated=Resource.quantity_allocated + data.quantity)
    )
    if result.rowcount != 1:
        db.rollback()
        raise conflict("Not enough stock left for that quantity.")
    dist = ResourceDistribution(
        resource_id=r.id, beneficiary_id=data.beneficiary_id, quantity=data.quantity,
        distribution_date=data.distribution_date or date.today(),
    )
    db.add(dist)
    db.flush()
    log_action(db, user, "DISTRIBUTE_RESOURCE", "ResourceDistribution", dist.id,
               {"resource_id": r.id, "beneficiary_id": data.beneficiary_id, "quantity": data.quantity})
    db.commit()
    db.refresh(r)
    return _dist_out(db.scalar(
        select(ResourceDistribution)
        .options(joinedload(ResourceDistribution.resource), joinedload(ResourceDistribution.beneficiary))
        .where(ResourceDistribution.id == dist.id)))


@router.get("/resources/{resource_id}/distributions", response_model=Page[DistributionOut])
def list_distributions(resource_id: int, ngo: CurrentNgo, db: DbSession, params: Annotated[PageParams, Depends()]):
    _owned_resource(db, resource_id, ngo)
    stmt = (select(ResourceDistribution)
            .options(joinedload(ResourceDistribution.resource), joinedload(ResourceDistribution.beneficiary))
            .where(ResourceDistribution.resource_id == resource_id)
            .order_by(ResourceDistribution.distribution_date.desc(), ResourceDistribution.id.desc()))
    return paginate(db, stmt, params, _dist_out)


# --------------------------------------------------------------- beneficiaries

@router.post("/campaigns/{campaign_id}/beneficiaries", response_model=CampaignBeneficiaryOut, status_code=201)
def enroll(campaign_id: int, data: BeneficiaryEnroll, ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    campaign = _writable_campaign(db, campaign_id, ngo)
    if data.email is not None:
        target = db.scalar(select(User).where(User.email == data.email.lower(), User.role == Role.BENEFICIARY))
        beneficiary = db.scalar(select(Beneficiary).where(Beneficiary.user_id == target.id)) if target else None
        if beneficiary is None:
            raise not_found("Registered beneficiary with that email")
    else:
        beneficiary = Beneficiary(
            name=data.name.strip(), contact=data.contact, location=data.location,
            required_assistance=data.required_assistance,
        )
        db.add(beneficiary)
        db.flush()
    if db.scalar(select(CampaignBeneficiary.id).where(
        CampaignBeneficiary.campaign_id == campaign.id, CampaignBeneficiary.beneficiary_id == beneficiary.id
    )):
        raise conflict("Already enrolled in this campaign.")
    link = CampaignBeneficiary(campaign_id=campaign.id, beneficiary_id=beneficiary.id)
    db.add(link)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise conflict("Already enrolled in this campaign.") from None
    log_action(db, user, "ENROLL_BENEFICIARY", "CampaignBeneficiary", link.id,
               {"campaign_id": campaign.id, "beneficiary_id": beneficiary.id})
    db.commit()
    return _link_out(link)


@router.get("/campaigns/{campaign_id}/beneficiaries", response_model=list[CampaignBeneficiaryOut])
def list_beneficiaries(campaign_id: int, ngo: CurrentNgo, db: DbSession):
    campaign_svc.get_owned_campaign(db, campaign_id, ngo)
    links = db.scalars(select(CampaignBeneficiary).options(joinedload(CampaignBeneficiary.beneficiary))
                       .where(CampaignBeneficiary.campaign_id == campaign_id)
                       .order_by(CampaignBeneficiary.id))
    return [_link_out(link) for link in links]


@router.patch("/campaigns/{campaign_id}/beneficiaries/{beneficiary_id}", response_model=CampaignBeneficiaryOut)
def update_support(campaign_id: int, beneficiary_id: int, data: SupportUpdate,
                   ngo: VerifiedNgo, user: CurrentUser, db: DbSession):
    _writable_campaign(db, campaign_id, ngo)
    link = db.scalar(select(CampaignBeneficiary).options(joinedload(CampaignBeneficiary.beneficiary)).where(
        CampaignBeneficiary.campaign_id == campaign_id, CampaignBeneficiary.beneficiary_id == beneficiary_id))
    if link is None:
        raise not_found("Enrollment")
    previous = link.support_status
    link.support_status = data.support_status
    log_action(db, user, "UPDATE_SUPPORT_STATUS", "CampaignBeneficiary", link.id,
               {"from": previous.value, "to": data.support_status.value})
    db.commit()
    return _link_out(link)


@router.get("/support/me", response_model=list[MySupportOut])
def my_support(user: BeneficiaryUser, db: DbSession):
    """A beneficiary sees only their own enrollment and what they themselves received."""
    beneficiary = db.scalar(select(Beneficiary).where(Beneficiary.user_id == user.id))
    if beneficiary is None:
        return []
    links = db.scalars(select(CampaignBeneficiary)
                       .options(joinedload(CampaignBeneficiary.campaign).joinedload(Campaign.ngo))
                       .where(CampaignBeneficiary.beneficiary_id == beneficiary.id)
                       .order_by(CampaignBeneficiary.id)).all()
    out = []
    for link in links:
        dists = db.scalars(select(ResourceDistribution).options(joinedload(ResourceDistribution.resource))
                           .where(ResourceDistribution.beneficiary_id == beneficiary.id,
                                  ResourceDistribution.resource.has(campaign_id=link.campaign_id))
                           .order_by(ResourceDistribution.distribution_date)).all()
        out.append(MySupportOut(
            campaign_id=link.campaign_id, campaign_title=link.campaign.title,
            ngo_name=link.campaign.ngo.ngo_name, support_status=link.support_status,
            received=[{"resource": d.resource.name, "unit": d.resource.unit, "quantity": d.quantity,
                       "date": d.distribution_date.isoformat()} for d in dists],
        ))
    return out


