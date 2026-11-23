"""Central API router aggregating feature routes."""

from fastapi import APIRouter
from app.api.routes import (
    admin,
    agenda,
    analytics,
    auth,
    business_matching,
    business_profile,
    chatroom,
    conversations,
    events,
    group_conversations,
    health,
    matching,
    organizer,
    profile,
    proposals,
    quote,
    brochures,
    version,
)

api_router = APIRouter()

# Include foundation, identity, agenda, matching, conversation, analytics, admin, organizer, real-time events, business profile, group circles, chatroom, proposal, quote, and digital brochure routes
api_router.include_router(health.router)
api_router.include_router(version.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(business_profile.router)
api_router.include_router(business_matching.router)
api_router.include_router(agenda.router)
api_router.include_router(matching.router)
api_router.include_router(conversations.router)
api_router.include_router(group_conversations.router)
api_router.include_router(chatroom.router)
api_router.include_router(proposals.router)
api_router.include_router(quote.router)
api_router.include_router(brochures.router)
api_router.include_router(analytics.router)
api_router.include_router(admin.router)
api_router.include_router(organizer.router)
api_router.include_router(events.router)
