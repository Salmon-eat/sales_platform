from fastapi import APIRouter, Depends

from app.api.deps import require_staff
from app.api.routes import (
    account,
    admin,
    admin_analytics,
    admin_companies,
    admin_listings,
    admin_moderation,
    admin_orders,
    admin_reports,
    admin_users,
    analytics,
    applications,
    auth,
    bot_sync,
    companies,
    contacts,
    health,
    home,
    listings,
    locations,
    my,
    pages,
    payments,
    posts,
    reports,
    sellers,
    taxonomy,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(home.router)
api_router.include_router(taxonomy.router)
api_router.include_router(locations.router)
api_router.include_router(listings.router)
api_router.include_router(pages.router)
api_router.include_router(applications.router)
api_router.include_router(applications.chat_router)
api_router.include_router(auth.router)
api_router.include_router(account.router)
api_router.include_router(my.router)
api_router.include_router(contacts.router)
api_router.include_router(reports.router)
api_router.include_router(sellers.router)
api_router.include_router(companies.router)
api_router.include_router(payments.router)
api_router.include_router(posts.router)
api_router.include_router(analytics.router)
api_router.include_router(bot_sync.router)

# /admin/*: staff only at the router level as well, so a new endpoint without its own check is still
# closed; admin-only endpoints add require_admin on top (admin spec §1, §9).
admin_router = APIRouter(dependencies=[Depends(require_staff)])
admin_router.include_router(admin.router)
admin_router.include_router(admin_listings.router)
admin_router.include_router(admin_moderation.router)
admin_router.include_router(admin_reports.router)
admin_router.include_router(admin_companies.router)
admin_router.include_router(admin_orders.router)
admin_router.include_router(posts.admin_router)
admin_router.include_router(admin_analytics.router)
admin_router.include_router(admin_users.router)
api_router.include_router(admin_router)
