"""The visitor's own ads: write one, attach photos, send it for checking, close it.

Everything here is about the person's own rows only: each handler looks the ad up by id *and* owner,
so an id guessed from someone else's page leads nowhere.
"""

from datetime import datetime
from urllib.parse import quote, unquote

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.deps import CurrentUser, RedisDep, SessionDep
from app.core.config import settings
from pydantic import BaseModel, Field

from app.models import Order, Resume
from app.models.listing import MAX_PHOTOS
from app.models.review import MAX_REPLY, MAX_REVIEW
from app.schemas.chat import ChatItem, ChatOut, MessageIn, StartChatIn
from app.schemas.common import Lang
from app.schemas.company import CompanyActionIn, CompanyIn, MyCompanyOut
from app.schemas.employer import CandidateOut, NoteIn, StatusIn
from app.schemas.my import MyActionIn, MyListingIn, MyListingItem, MyListingOut, PhotoOut
from app.schemas.resume import ApplyIn, ApplyOut, ResumeIn, ResumeOut
from app.services import (
    chats,
    companies,
    cv,
    employer,
    my_listings,
    payments,
    photos,
    resumes,
    reviews,
    searches,
)

router = APIRouter(prefix="/my", tags=["my"])


@router.get("/listings", response_model=list[MyListingItem])
async def my_ads(user: CurrentUser, session: SessionDep, lang: Lang = "es") -> list[MyListingItem]:
    return await my_listings.mine(session, user, lang)


@router.post("/listings", response_model=MyListingOut, status_code=status.HTTP_201_CREATED)
async def create(
    body: MyListingIn, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> MyListingOut:
    listing = await my_listings.save(session, user, body)
    return await my_listings.detail_out(session, listing, lang)


@router.get("/listings/{listing_id}", response_model=MyListingOut)
async def one(
    listing_id: int, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> MyListingOut:
    listing = await my_listings.get_own(session, user, listing_id)
    return await my_listings.detail_out(session, listing, lang)


@router.put("/listings/{listing_id}", response_model=MyListingOut)
async def update(
    listing_id: int, body: MyListingIn, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> MyListingOut:
    listing = await my_listings.get_own(session, user, listing_id)
    listing = await my_listings.save(session, user, body, listing)
    return await my_listings.detail_out(session, listing, lang)


@router.post("/listings/{listing_id}/actions", response_model=MyListingOut)
async def act(
    listing_id: int, body: MyActionIn, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> MyListingOut:
    listing = await my_listings.get_own(session, user, listing_id)
    listing = await my_listings.act(session, user, listing, body.action)
    return await my_listings.detail_out(session, listing, lang)


@router.delete("/listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(listing_id: int, user: CurrentUser, session: SessionDep) -> None:
    listing = await my_listings.get_own(session, user, listing_id)
    await my_listings.remove(session, listing)


@router.post("/listings/{listing_id}/photos", response_model=PhotoOut, status_code=status.HTTP_201_CREATED)
async def add_photo(
    listing_id: int, request: Request, user: CurrentUser, session: SessionDep
) -> PhotoOut:
    """One photo as the raw request body, like the CV upload: no form encoding, no extra library."""
    listing = await my_listings.get_own(session, user, listing_id)
    if int(request.headers.get("content-length") or 0) > photos.MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > photos.MAX_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
    row = await my_listings.add_photo(session, user, listing, bytes(data))
    return PhotoOut(
        id=row.id, path=row.path, thumb=photos.thumb_path(row.path), width=row.width, height=row.height
    )


@router.delete("/listings/{listing_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def drop_photo(
    listing_id: int, photo_id: int, user: CurrentUser, session: SessionDep
) -> None:
    listing = await my_listings.get_own(session, user, listing_id)
    await my_listings.drop_photo(session, listing, photo_id)


# ---------------------------------------------------------------------------- messages


@router.get("/chats", response_model=list[ChatItem])
async def my_chats(user: CurrentUser, session: SessionDep, lang: Lang = "es") -> list[ChatItem]:
    return await chats.mine(session, user, lang)


@router.post("/chats", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
async def write_to_seller(
    body: StartChatIn, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> ChatOut:
    """The buyer's first message about an ad; writing again continues the same conversation."""
    chat = await chats.start(session, user, body.listing_id, body.text)
    return await chats.detail_out(session, chat, user, lang)


@router.get("/chats/{chat_id}", response_model=ChatOut)
async def read_chat(
    chat_id: int, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> ChatOut:
    chat = await chats.get_own(session, user, chat_id)
    await chats.mark_read(session, chat, user)
    return await chats.detail_out(session, chat, user, lang)


@router.post("/chats/{chat_id}/messages", response_model=ChatOut)
async def reply(
    chat_id: int, body: MessageIn, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> ChatOut:
    chat = await chats.get_own(session, user, chat_id)
    await chats.add_message(session, chat, user, body.text)
    return await chats.detail_out(session, chat, user, lang)


@router.post("/chats/{chat_id}/hide", status_code=status.HTTP_204_NO_CONTENT)
async def hide_chat(chat_id: int, user: CurrentUser, session: SessionDep) -> None:
    """Out of my list; the other side keeps the conversation and can write again."""
    await chats.hide(session, await chats.get_own(session, user, chat_id), user)


@router.get("/unread")
async def unread(user: CurrentUser, session: SessionDep) -> dict[str, int]:
    """For the badge in the header."""
    return {"messages": await chats.unread_total(session, user)}


# ---------------------------------------------------------------------------- the candidate's CV


async def _my_resume(session: SessionDep, user: CurrentUser) -> Resume:
    resume = await resumes.get(session, user)
    if resume is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no_resume")
    return resume


@router.get("/resume", response_model=ResumeOut | None)
async def my_resume(user: CurrentUser, session: SessionDep, lang: Lang = "es") -> ResumeOut | None:
    """Null when there is none yet: the page then shows an empty form, not an error."""
    resume = await resumes.get(session, user)
    return await resumes.out(session, resume, lang) if resume else None


@router.put("/resume", response_model=ResumeOut)
async def save_resume(
    body: ResumeIn, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> ResumeOut:
    resume = await resumes.save(session, user, body)
    return await resumes.out(session, resume, lang)


@router.post("/resume/file", response_model=ResumeOut)
async def upload_resume_file(
    request: Request, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> ResumeOut:
    """The CV file itself: raw body, name in X-File-Name, like the file sent with an application."""
    resume = await _my_resume(session, user)
    if int(request.headers.get("content-length") or 0) > cv.MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > cv.MAX_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
    name = unquote(request.headers.get("x-file-name") or "")[:200]
    resume = await resumes.attach_file(session, resume, bytes(data), name)
    return await resumes.out(session, resume, lang)


@router.delete("/resume/file", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume_file(user: CurrentUser, session: SessionDep) -> None:
    await resumes.drop_file(session, await _my_resume(session, user))


@router.delete("/resume", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(user: CurrentUser, session: SessionDep) -> None:
    await resumes.remove(session, await _my_resume(session, user))


@router.post("/apply", response_model=ApplyOut, status_code=status.HTTP_201_CREATED)
async def apply_with_resume(body: ApplyIn, user: CurrentUser, session: SessionDep) -> ApplyOut:
    """One press on a vacancy: the application goes to the managers with the CV attached."""
    return await resumes.apply(session, user, await _my_resume(session, user), body)


# ---------------------------------------------------------------------------- answers to my vacancies


@router.get("/candidates", response_model=list[CandidateOut])
async def my_candidates(
    user: CurrentUser,
    session: SessionDep,
    lang: Lang = "es",
    listing_id: int | None = None,
) -> list[CandidateOut]:
    """Everyone who answered a vacancy this person posted; nothing from anybody else's listings."""
    return await employer.candidates(session, user, lang, listing_id)


@router.post("/candidates/{application_id}/status", response_model=CandidateOut)
async def set_candidate_status(
    application_id: int, body: StatusIn, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> CandidateOut:
    application = await employer.get_application(session, user, application_id)
    await employer.set_status(session, application, body.status)
    return await employer.out(session, application, lang)


@router.post("/candidates/{application_id}/notes", response_model=CandidateOut)
async def add_candidate_note(
    application_id: int, body: NoteIn, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> CandidateOut:
    application = await employer.get_application(session, user, application_id)
    await employer.add_note(session, application, user, body.text)
    return await employer.out(session, application, lang)


@router.get("/candidates/{application_id}/cv")
async def candidate_cv(application_id: int, user: CurrentUser, session: SessionDep) -> Response:
    """Always a download, never opened in the browser: an uploaded file is not our page."""
    application = await employer.get_application(session, user, application_id)
    row = await employer.cv_file(session, application)
    return Response(
        content=row.data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(row.filename)}",
            "X-Content-Type-Options": "nosniff",
        },
    )


# ---------------------------------------------------------------------------- saved searches


class SearchIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    section_key: str | None = Field(None, max_length=50)
    category_slug: str | None = Field(None, max_length=120)
    location_slug: str | None = Field(None, max_length=120)
    params: dict[str, str] = Field(default_factory=dict, max_length=20)


class SearchOut(BaseModel):
    id: int
    title: str
    lang: str
    section_key: str | None
    category_slug: str | None
    location_slug: str | None
    params: dict[str, str]
    notify: bool
    created_at: datetime
    last_notified_at: datetime | None


class NotifyIn(BaseModel):
    notify: bool


@router.get("/searches", response_model=list[SearchOut])
async def my_searches(user: CurrentUser, session: SessionDep) -> list[SearchOut]:
    rows = await searches.mine(session, user)
    return [SearchOut.model_validate(row, from_attributes=True) for row in rows]


@router.post("/searches", response_model=SearchOut, status_code=status.HTTP_201_CREATED)
async def save_search(
    body: SearchIn, user: CurrentUser, session: SessionDep, redis: RedisDep, lang: Lang = "es"
) -> SearchOut:
    """Saved as it stands; the first letter is about what appears after this moment."""
    search = await searches.save(
        session,
        redis,
        user,
        title=body.title,
        lang=lang,
        section_key=body.section_key,
        category_slug=body.category_slug,
        location_slug=body.location_slug,
        params=body.params,
    )
    return SearchOut.model_validate(search, from_attributes=True)


@router.post("/searches/{search_id}/notify", response_model=SearchOut)
async def toggle_notify(
    search_id: int, body: NotifyIn, user: CurrentUser, session: SessionDep
) -> SearchOut:
    search = await searches.set_notify(session, user, search_id, body.notify)
    return SearchOut.model_validate(search, from_attributes=True)


@router.delete("/searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search(search_id: int, user: CurrentUser, session: SessionDep) -> None:
    await searches.remove(session, user, search_id)


# ---------------------------------------------------------------------------- paid extras


class OrderIn(BaseModel):
    product: str = Field(max_length=30)
    # the ad or the firm it is for
    target_id: int


class OrderOut(BaseModel):
    id: int
    product: str
    days: int
    amount: int
    currency: str
    status: str
    listing_id: int | None
    company_id: int | None
    created_at: datetime
    paid_at: datetime | None


@router.get("/orders", response_model=list[OrderOut])
async def my_orders(user: CurrentUser, session: SessionDep) -> list[OrderOut]:
    rows = await payments.my_orders(session, user)
    return [OrderOut.model_validate(row, from_attributes=True) for row in rows]


@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(body: OrderIn, user: CurrentUser, session: SessionDep) -> OrderOut:
    """Written down first; nothing is switched on until the money is there."""
    order = await payments.create(session, user, body.product, body.target_id)
    return OrderOut.model_validate(order, from_attributes=True)


@router.post("/orders/{order_id}/checkout")
async def checkout(order_id: int, user: CurrentUser, session: SessionDep) -> dict[str, str]:
    """A link to Stripe's own page; card details never touch this server."""
    order = await session.get(Order, order_id)
    if order is None or order.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    if order.status == "paid":
        raise HTTPException(status.HTTP_409_CONFLICT, "already_paid")
    site = settings.public_site_url.rstrip("/")
    url = await payments.checkout_url(
        order,
        f"Citobazar · {order.product}",
        f"{site}/es/cuenta?paid={order.id}",
        f"{site}/es/cuenta?cancelled={order.id}",
    )
    return {"url": url}


# ---------------------------------------------------------------------------- my firm


@router.get("/company", response_model=MyCompanyOut | None)
async def my_company(user: CurrentUser, session: SessionDep, lang: Lang = "es") -> MyCompanyOut | None:
    firm = await companies.get_own(session, user)
    return await companies.mine_out(session, firm, lang) if firm else None


@router.put("/company", response_model=MyCompanyOut)
async def save_company(
    body: CompanyIn, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> MyCompanyOut:
    firm = await companies.save(session, user, body)
    return await companies.mine_out(session, firm, lang)


@router.post("/company/actions", response_model=MyCompanyOut)
async def company_action(
    body: CompanyActionIn, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> MyCompanyOut:
    firm = await companies.act(session, user, body.action)
    return await companies.mine_out(session, firm, lang)


@router.post("/company/logo", response_model=MyCompanyOut)
async def company_logo(
    request: Request, user: CurrentUser, session: SessionDep, lang: Lang = "es"
) -> MyCompanyOut:
    """One picture, handled like an ad's photo: turned upright, stripped of metadata, resized."""
    firm = await companies.get_own(session, user)
    if firm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no_company")
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > photos.MAX_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
    old = firm.logo
    firm.logo = photos.save(bytes(data))[0]
    await session.commit()
    await session.refresh(firm)
    if old:
        photos.delete(old)
    return await companies.mine_out(session, firm, lang)


@router.delete("/company", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(user: CurrentUser, session: SessionDep) -> None:
    firm = await companies.get_own(session, user)
    logo = firm.logo if firm else None
    await companies.remove(session, user)
    if logo:
        photos.delete(logo)


# ---------------------------------------------------------------------------- reviews


class ReviewIn(BaseModel):
    seller_id: int
    rating: int = Field(ge=1, le=5)
    text: str = Field("", max_length=MAX_REVIEW)
    listing_id: int | None = None


class ReplyIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_REPLY)


@router.get("/reviews")
async def my_reviews(user: CurrentUser, session: SessionDep) -> dict[str, list[dict]]:
    """Both sides: what people said about me, and what I said about others."""
    return {
        "about_me": await reviews.about(session, user.id),
        "written": await reviews.written_by(session, user),
    }


@router.post("/reviews", status_code=status.HTTP_201_CREATED)
async def leave_review(body: ReviewIn, user: CurrentUser, session: SessionDep) -> dict:
    review = await reviews.leave(
        session, user, body.seller_id, body.rating, body.text.strip(), body.listing_id
    )
    return await reviews.as_dict(session, review)


@router.delete("/reviews/{seller_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(seller_id: int, user: CurrentUser, session: SessionDep) -> None:
    await reviews.remove(session, user, seller_id)


@router.post("/reviews/{review_id}/reply")
async def reply_to_review(
    review_id: int, body: ReplyIn, user: CurrentUser, session: SessionDep
) -> dict:
    review = await reviews.answer(session, user, review_id, body.text.strip())
    return await reviews.as_dict(session, review)


@router.get("/limits")
async def limits(user: CurrentUser, session: SessionDep) -> dict[str, int]:
    """What the form needs to know before it lets someone start another ad."""
    return {
        "open": await my_listings.count_open(session, user),
        "max_listings": settings.listings_per_user,
        "max_photos": MAX_PHOTOS,
        "days": settings.listing_days,
    }
