"""Ambient Lounge Service powering the continuous interval open conference chatroom."""

import json
import logging
import random
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.agenda import ConferenceLiveState, ConferenceLiveStateEnum, Session
from app.db.models.chatroom import (
    ChatroomMessage,
    ChatroomMessageKind,
    ChatroomPresence,
    ChatroomSenderType,
    ConferenceChatroom,
)
from app.db.models.conversation import Conversation, ConversationStatus, Message, MessageSenderType
from app.db.models.profile import ParticipantProfile
from app.db.models.user import User
from app.services.temporal_context import TemporalContextService
from app.services.traffic_service import TrafficService
from app.services.weather_service import WeatherService

logger = logging.getLogger(__name__)

# --- Rich Diverse Conversational Prompts for the Conference Lounge (Fun, Vibrant, Anti-Repetitive) ---

VENUE_HACKS_TEMPLATES = [
    "🔌 Delegate Pro-Tip: Running low on battery? High-speed charging sockets are available at {charging_loc}! Free to use anytime.",
    "🔋 Battery top-up: If your laptop or tablet needs juice between tracks, head over to the charging docks at {charging_loc}.",
    "❄️ Venue Temperature Tip: Hall A's AC is running on Arctic mode today ❄️🥶 Highly recommend keeping a blazer handy if you're settling in for the long keynote!",
    "☕ Secret Coffee Tip: The South Indian filter coffee station behind the exhibition booths currently has zero queue compared to the main concourse! 🤫☕",
    "🍪 Refreshment Desk: Fresh warm almond cookies and spiced tea just restocked at the Central Concourse counter! Go, go, go! 🏃‍♂️🍪",
    "🏷️ Badge Check: Quick glance down to flip your lanyard badge right-side-up—half the hall is wearing their badges backwards today 😄🏷️",
    "📊 Presentation Slide Kudos: Shout-out to the presenters who used 24pt+ fonts on their technical slides today—our eyes in the back rows thank you! 🙌",
]

ICEBREAKER_QUESTIONS = [
    "☕ Quick poll for everyone in the lounge: Are you team Hot Masala Chai or Dark Roast Espresso today? Drop a note below!",
    "🎙️ For anyone who attended the morning sessions: What was the one takeaway or chart that caught your attention most?",
    "🌱 The lounge is buzzing today! If you are working on green procurement, LC3 binders, or alternative fuels, say hi!",
    "🍪 Pro-tip: The refreshment counter near the Central Concourse just put out warm almond cookies and ginger biscuits. Perfect break fuel!",
    "💡 Delegate Tip: If you are exploring bilateral partnerships, you can initiate a 1-on-1 AI representative alignment anytime from the attendee directory.",
    "📍 What's everyone's home city for this conference? Pune, Mumbai, Nashik, Bengaluru, Hyderabad, or visiting internationally?",
    "🏢 Anyone visited the technology exhibition stalls in Hall B yet? Some impressive automation demos and test equipment over there.",
    "👟 Exhibition floor walking tour check: My step count is already past 7,500! How are everyone's feet holding up today? 😄",
    "☕ The third cup of coffee is kicking in right on time for the upcoming technical tracks! Who else is fueling up?",
    "🍽️ Quick lunch/dinner debate: What's the best local food recommendation around the venue area for after the summit concludes?",
    "🤝 Looking to brainstorm on regional distribution, aggregate supply, or low-carbon mixes? Drop a message or reply here!",
    "📊 Quick show of hands: Is your team currently seeing higher client interest in commercial compliance or green ESG certifications this quarter?",
    "✨ The networking atmosphere in the hall is great today. Don't hesitate to reach out to fellow delegates in the lounge!",
    "🚗 How was the morning travel for everyone driving in from expressway corridors? Smooth sailing or early bottlenecks?",
    "🎯 If you could solve one operational bottleneck in your supply chain this fiscal year, what would it be?",
    "🥤 Afternoon energy poll: ☕ Masala Chai vs ☕ Double Espresso vs 🥤 Fresh Lime Soda to power through the 3 PM sessions?",
    "🛣️ Commute show of hands: Who drove the expressway corridor this morning vs flew into the city airport? How was the drive?",
    "🎯 If your team could automate one manual operational workflow this fiscal year, what would you pick?",
]


SESSION_BUZZ_PROMPTS_DAY_1 = [
    "The morning keynote on LC3 calcined clay standardization had some very realistic cost-per-tonne figures. Definitely worth digging deeper.",
    "Interesting point from Hall A on raw kaolinitic clay calcination: keeping temperature strictly between 750-800°C prevents dead-burning.",
    "Great to see delegates across EPC, logistics, and mineral feedstocks actively comparing notes on Day 1 pilot trial specifications.",
    "The speaker's benchmark slide on blended cement 28-day hydration curves sparked some great debates in the concourse!",
    "Excited about the transition towards standardized Bureau of Indian Standards (BIS) composite blended cement codes discussed this morning.",
]

SESSION_BUZZ_PROMPTS_DAY_2 = [
    "Day 2 morning track on site execution really put the spotlight on 3-day early compressive strength vs precast demoulding cycles.",
    "Fascinating debate in Hall B: polycarboxylate ether (PCE) superplasticizers compatibility when switching clinker replacement to 45%.",
    "Contractors and concrete producers in the corridor are debating whether water demand increase in LC3 can be mitigated without high admixture costs.",
    "Key takeaway from Day 2 logistics panel: regional quarry-to-calciner supply chains cut transport emissions far more than imported additives.",
    "The field case study on highway bridge pier carbonation depth over 48 months showed LC3 matching traditional OPC 53 durability.",
]

SESSION_BUZZ_PROMPTS = SESSION_BUZZ_PROMPTS_DAY_1

AVATAR_BANTER_TEMPLATES_DAY_1 = [
    "Hi everyone! Representing {company}. On Day 1, our primary focus is {topic_focus}. If anyone in the lounge is tracking the BIS LC3 code revisions, let's connect over coffee!",
    "Checking in from {company}'s desk. We are benchmarking clinker factor reduction and calcined clay sourcing on {topic_focus}. Feel free to say hello!",
    "Greetings from {company}! Really encouraging insights from the morning keynotes on {topic_focus}. Always keen to explore trial collaborations with fellow delegates.",
    "Hello delegates! At {company}, we are evaluating regional raw clay supply viability for {topic_focus}. Happy to discuss testing parameters with industry peers.",
]

AVATAR_BANTER_TEMPLATES_DAY_2 = [
    "Checking in on Day 2 from {company}! We're analyzing field test reports and contractor feedback around {topic_focus}. Anyone else tracking demoulding turnaround times?",
    "Greetings from {company}'s team! Day 2 discussions on batching plant quality control and {topic_focus} hit right at the heart of operational scale. Let's compare notes!",
    "Hello everyone! At {company}, our focus today is field durability and supply agreements in {topic_focus}. Looking forward to connecting with procurement and EPC partners.",
    "Representing {company} in the lounge. We're examining early-strength gain data versus 28-day curing curves for {topic_focus}. Keen to hear how other sites are tackling it!",
]

AVATAR_BANTER_TEMPLATES = AVATAR_BANTER_TEMPLATES_DAY_1


class AmbientLoungeService:
    """Orchestrates public chatroom presence, user messaging, and continuous ambient dialogue flow."""

    @classmethod
    async def get_or_create_default_lounge(
        cls,
        db: AsyncSession,
        conference_id: Optional[uuid.UUID] = None,
    ) -> ConferenceChatroom:
        """Fetch or automatically initialize the dedicated Conference Networking Lounge."""
        # 1. Resolve target conference: passed conference_id or first active conference
        target_conf = await TemporalContextService.get_active_conference(db, conference_id)
        target_conf_id = target_conf.id if target_conf else None

        lounge = None

        # 2. Look for existing lounge explicitly bound to this conference
        if target_conf_id:
            query = select(ConferenceChatroom).where(ConferenceChatroom.conference_id == target_conf_id)
            result = await db.execute(query)
            lounge = result.scalar_one_or_none()

        # 3. If no conference-bound lounge, check if an unassigned lounge exists from legacy data
        if not lounge and target_conf_id:
            unassigned_query = select(ConferenceChatroom).where(
                ConferenceChatroom.conference_id.is_(None),
                ConferenceChatroom.slug == "networking-lounge",
            )
            res_unassigned = await db.execute(unassigned_query)
            unassigned = res_unassigned.scalar_one_or_none()
            if unassigned:
                # Rebind unassigned lounge to the active conference
                unassigned.conference_id = target_conf_id
                unassigned.name = f"{target_conf.title} — Networking Lounge"
                unassigned.slug = f"lounge-{target_conf_id.hex[:8]}"
                unassigned.description = (
                    f"Official open public networking lounge for delegates attending "
                    f"{target_conf.title} at {target_conf.venue_name}."
                )
                await db.commit()
                await db.refresh(unassigned)
                lounge = unassigned

        # 4. If still no lounge, check fallback slug
        if not lounge:
            fallback_slug = f"lounge-{target_conf_id.hex[:8]}" if target_conf_id else "networking-lounge"
            slug_query = select(ConferenceChatroom).where(ConferenceChatroom.slug == fallback_slug)
            res_slug = await db.execute(slug_query)
            lounge = res_slug.scalar_one_or_none()

        # 5. Create new lounge if none found
        if not lounge:
            conf_title = target_conf.title if target_conf else "Converge AI Summit"
            venue_name = target_conf.venue_name if target_conf else "Conference Venue"
            slug_val = f"lounge-{target_conf_id.hex[:8]}" if target_conf_id else "networking-lounge"
            lounge = ConferenceChatroom(
                conference_id=target_conf_id,
                name=f"{conf_title} — Networking Lounge" if target_conf else "The Networking Lounge",
                slug=slug_val,
                description=f"Open public lounge for delegates attending {conf_title} at {venue_name}.",
                is_active=True,
                ambient_interval_seconds=25,
            )
            db.add(lounge)
            await db.commit()
            await db.refresh(lounge)

        # 6. Ensure at least one welcome message exists
        msg_count_query = select(func.count(ChatroomMessage.id)).where(ChatroomMessage.chatroom_id == lounge.id)
        msg_count_res = await db.execute(msg_count_query)
        if (msg_count_res.scalar() or 0) == 0:
            conf_title = target_conf.title if target_conf else "Converge AI Summit"
            venue = target_conf.venue_name if target_conf else "the conference center"
            welcome_msg = ChatroomMessage(
                chatroom_id=lounge.id,
                sender_id=None,
                sender_type=ChatroomSenderType.HOST.value,
                sender_name="Virtual Lounge Host",
                content=(
                    f"🎉 Welcome to the {conf_title} Networking Lounge at {venue}! "
                    f"This is an open town square for all delegates to chat, share session takeaways, "
                    f"connect on mutual initiatives, and stay posted on break announcements, live weather, and venue updates."
                ),
                message_kind=ChatroomMessageKind.WELCOME.value,
                turn_index=0,
            )
            db.add(welcome_msg)
            await db.commit()

        return lounge

    @classmethod
    async def join_lounge(
        cls,
        db: AsyncSession,
        chatroom_id: uuid.UUID,
        user: User,
    ) -> Tuple[ChatroomPresence, Optional[ChatroomMessage]]:
        """Register user presence and generate a warm joiner introduction if new."""
        now = datetime.now(timezone.utc)

        pres_query = select(ChatroomPresence).where(
            ChatroomPresence.chatroom_id == chatroom_id,
            ChatroomPresence.user_id == user.id,
        )
        res = await db.execute(pres_query)
        presence = res.scalar_one_or_none()

        welcome_msg = None
        is_first_join = False

        if not presence:
            presence = ChatroomPresence(
                chatroom_id=chatroom_id,
                user_id=user.id,
                is_online=True,
                last_seen_at=now,
            )
            db.add(presence)
            is_first_join = True
        else:
            # If was offline for > 15 mins, treat as fresh arrival
            if not presence.is_online or (presence.last_seen_at and (now - presence.last_seen_at).total_seconds() > 900):
                is_first_join = True
            presence.is_online = True
            presence.last_seen_at = now

        if is_first_join:
            org_str = f" from {user.company_name}" if user and user.company_name else ""
            hobbies_str = ""

            user_query = select(User).options(selectinload(User.hobbies)).where(User.id == user.id)
            user_res = await db.execute(user_query)
            user_with_hobbies = user_res.scalar_one_or_none()

            if user_with_hobbies and user_with_hobbies.hobbies:
                top_hobbies = [h.hobby_name for h in user_with_hobbies.hobbies[:2]]
                hobbies_str = f" Outside of sessions, interested in {' and '.join(top_hobbies)}."

            next_turn = await cls._get_next_turn_index(db, chatroom_id)
            welcome_msg = ChatroomMessage(
                chatroom_id=chatroom_id,
                sender_id=None,
                sender_type=ChatroomSenderType.HOST.value,
                sender_name="Virtual Lounge Host",
                content=f"👋 Everyone welcome {user.full_name}{org_str} to the lounge!{hobbies_str} Feel free to say hi!",
                message_kind=ChatroomMessageKind.WELCOME.value,
                turn_index=next_turn,
            )
            db.add(welcome_msg)

        await db.commit()
        await db.refresh(presence)
        return presence, welcome_msg

    @classmethod
    async def leave_lounge(
        cls,
        db: AsyncSession,
        chatroom_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Mark user presence offline."""
        stmt = (
            update(ChatroomPresence)
            .where(
                ChatroomPresence.chatroom_id == chatroom_id,
                ChatroomPresence.user_id == user_id,
            )
            .values(is_online=False, last_seen_at=datetime.now(timezone.utc))
        )
        await db.execute(stmt)
        await db.commit()

    @classmethod
    async def post_user_message(
        cls,
        db: AsyncSession,
        chatroom_id: uuid.UUID,
        user: User,
        content: str,
    ) -> ChatroomMessage:
        """Post an attendee's human chat message into the stream."""
        next_turn = await cls._get_next_turn_index(db, chatroom_id)
        msg = ChatroomMessage(
            chatroom_id=chatroom_id,
            sender_id=user.id,
            sender_type=ChatroomSenderType.USER.value,
            sender_name=user.full_name,
            content=content.strip(),
            message_kind=ChatroomMessageKind.CHAT.value,
            turn_index=next_turn,
        )
        db.add(msg)

        presence_stmt = (
            update(ChatroomPresence)
            .where(
                ChatroomPresence.chatroom_id == chatroom_id,
                ChatroomPresence.user_id == user.id,
            )
            .values(is_online=True, last_seen_at=datetime.now(timezone.utc))
        )
        await db.execute(presence_stmt)

        await db.commit()
        await db.refresh(msg)
        return msg

    @classmethod
    async def broadcast_organizer_announcement(
        cls,
        db: AsyncSession,
        conference_id: uuid.UUID,
        announcement_text: str,
        message_kind: str = ChatroomMessageKind.TEA_ANNOUNCEMENT.value,
    ) -> Optional[ChatroomMessage]:
        """Post an official live organizer broadcast announcement into that conference's lounge."""
        lounge = await cls.get_or_create_default_lounge(db, conference_id=conference_id)
        if not lounge or not lounge.is_active:
            return None

        # Debounce identical announcements within 45 seconds to prevent rapid double-clicks
        latest_stmt = (
            select(ChatroomMessage)
            .where(ChatroomMessage.chatroom_id == lounge.id)
            .order_by(desc(ChatroomMessage.turn_index))
            .limit(1)
        )
        l_res = await db.execute(latest_stmt)
        latest_msg = l_res.scalar_one_or_none()
        if latest_msg and latest_msg.content.strip() == announcement_text.strip():
            now = datetime.now(timezone.utc)
            if (now - latest_msg.created_at).total_seconds() < 45:
                return latest_msg

        next_turn = await cls._get_next_turn_index(db, lounge.id)
        msg = ChatroomMessage(
            chatroom_id=lounge.id,
            sender_id=None,
            sender_type=ChatroomSenderType.HOST.value,
            sender_name="Organizer Live Broadcast",
            content=announcement_text,
            message_kind=message_kind,
            turn_index=next_turn,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    @classmethod
    async def generate_ambient_tick(
        cls,
        db: AsyncSession,
        chatroom_id: uuid.UUID,
        force: bool = False,
    ) -> Tuple[bool, Optional[str], Optional[ChatroomMessage]]:
        """Evaluate and generate periodic ambient conversation flow with robust anti-repetition memory."""
        lounge_query = select(ConferenceChatroom).where(ConferenceChatroom.id == chatroom_id)
        lounge_res = await db.execute(lounge_query)
        lounge = lounge_res.scalar_one_or_none()
        if not lounge or not lounge.is_active:
            return False, "Lounge inactive or not found", None

        # Fetch recent 25 messages for comprehensive anti-repetition memory
        recent_query = (
            select(ChatroomMessage)
            .where(ChatroomMessage.chatroom_id == chatroom_id)
            .order_by(desc(ChatroomMessage.turn_index))
            .limit(25)
        )
        recent_res = await db.execute(recent_query)
        recent_msgs = list(recent_res.scalars().all())
        last_msg = recent_msgs[0] if recent_msgs else None

        now = datetime.now(timezone.utc)
        min_interval = lounge.ambient_interval_seconds or 25

        if not force and last_msg and last_msg.created_at:
            delta = (now - last_msg.created_at).total_seconds()
            if delta < min_interval:
                return False, f"Interval not reached ({round(delta)}s / {min_interval}s)", None

        next_turn = (last_msg.turn_index + 1) if last_msg else 0

        # Memory sets to prevent repeated phrases and same-sender loops
        recent_contents_norm = {re.sub(r"\s+", " ", m.content.strip().lower()) for m in recent_msgs}
        recent_kinds = [m.message_kind for m in recent_msgs[:5]]
        recent_sender_ids = {m.sender_id for m in recent_msgs[:8] if m.sender_id}

        # Fetch live environmental context
        temp_state = await TemporalContextService.get_current_conference_state(db, lounge.conference_id)
        weather_data = await WeatherService.get_weather_summary()
        traffic_data = await TrafficService.get_traffic_summary()

        # Contextual Reply A: If a human participant spoke in the last 2 minutes, have a peer avatar reply contextually!
        if last_msg and last_msg.sender_type == ChatroomSenderType.USER.value and (now - last_msg.created_at).total_seconds() < 120:
            human_name = last_msg.sender_name.split()[0] if last_msg.sender_name else "there"
            user_query = (
                select(User)
                .options(selectinload(User.topics))
                .where(User.is_active == True, User.id != last_msg.sender_id)
                .order_by(func.random())
                .limit(1)
            )
            u_res = await db.execute(user_query)
            peer_user = u_res.scalar_one_or_none()

            if peer_user:
                sender_name = f"{peer_user.full_name}'s Representative"
                peer_company = peer_user.company_name or "our team"
                human_text = last_msg.content.lower()

                # Dynamic contextual matching based on keywords
                commercial_keywords = [
                    "quote", "quotation", "price", "pricing", "cost", "rfq", "procure", "procurement",
                    "supply agreement", "commercial", "vendor quote", "rate", "batch slump testing",
                    "demoulding", "tons", "contract", "purchase order", "trial batch"
                ]
                if any(w in human_text for w in commercial_keywords):
                    # Prajyot's Rule: Quotations and commercial terms cannot be discussed in public chatroom.
                    # Automatically initiate or resume private 1-on-1 thread under Messages & notify human!
                    try:
                        # Prajyot's Setting: Verify agent configuration for DM initiation for BOTH participants
                        human_prof_stmt = select(ParticipantProfile).where(ParticipantProfile.user_id == last_msg.sender_id)
                        human_prof = (await db.execute(human_prof_stmt)).scalar_one_or_none()
                        human_dm_enabled = getattr(human_prof, "allow_agent_dm_initiation", True) if human_prof else True

                        peer_prof_stmt = select(ParticipantProfile).where(ParticipantProfile.user_id == peer_user.id)
                        peer_prof = (await db.execute(peer_prof_stmt)).scalar_one_or_none()
                        peer_dm_enabled = getattr(peer_prof, "allow_agent_dm_initiation", True) if peer_prof else True

                        if last_msg.sender_id and human_dm_enabled and peer_dm_enabled:
                            active_conv_stmt = select(Conversation).where(
                                or_(
                                    (Conversation.initiator_id == peer_user.id) & (Conversation.target_id == last_msg.sender_id),
                                    (Conversation.initiator_id == last_msg.sender_id) & (Conversation.target_id == peer_user.id),
                                ),
                                Conversation.status.in_([ConversationStatus.INVITED, ConversationStatus.ACTIVE]),
                            )
                            conv = (await db.execute(active_conv_stmt)).scalar_one_or_none()
                            if not conv:
                                conv = Conversation(
                                    initiator_id=peer_user.id,
                                    target_id=last_msg.sender_id,
                                    status=ConversationStatus.ACTIVE,
                                )
                                db.add(conv)
                                await db.flush()
                            elif conv.status == ConversationStatus.INVITED:
                                conv.status = ConversationStatus.ACTIVE
                                await db.flush()

                            count_stmt = select(func.count(Message.id)).where(Message.conversation_id == conv.id)
                            msg_count = (await db.scalar(count_stmt)) or 0
                            if msg_count < 30:
                                private_briefing = (
                                    f"Hello {last_msg.sender_name}! In response to your inquiry in the Networking Lounge regarding "
                                    f"'{last_msg.content}', our technical and commercial desk at {peer_company} has initiated this private 1-on-1 thread. "
                                    f"Detailed quotations, batch trial specs, and logistics can be discussed here securely. "
                                    f"Our delegate {peer_user.full_name} has been notified for human takeover."
                                )
                                pm = Message(
                                    conversation_id=conv.id,
                                    sender_id=peer_user.id,
                                    sender_type=MessageSenderType.AGENT,
                                    content=private_briefing,
                                    turn_index=msg_count,
                                )
                                db.add(pm)
                                await db.flush()

                            reply_choices = [
                                f"🔒 High-Priority Commercial Inquiry: At {peer_company}, quotations, batch trial specs, and commercial rates are protected and cannot be disclosed in the public lounge. I've initiated a private 1-on-1 thread with {human_name} under Messages for our technical briefing.",
                                f"🔒 Commercial Handoff: Regarding commercial terms for '{last_msg.content[:40]}...', I've routed this to a private direct message thread with {human_name} under Messages to exchange quotation details privately with {peer_company}.",
                            ]
                        else:
                            reply_choices = [
                                f"Commercial Note: At {peer_company}, quotations and commercial parameters are protected and cannot be disclosed in the public lounge. Since private representative DM handoff is currently disabled in profile privacy settings, please connect directly during session breaks to review quotations.",
                            ]
                    except Exception as err:
                        logger.warning(f"Could not auto-bridge to private conversation: {err}")
                        reply_choices = [
                            f"Commercial Note: At {peer_company}, commercial rates and quotation specs are handled privately with authorized delegates.",
                        ]
                elif any(w in human_text for w in ["tea", "coffee", "chai", "snack", "cookie"]):
                    reply_choices = [
                        f"Great point, {human_name}! The tea counter in the Central Concourse has some fantastic fresh masala chai right now.",
                        f"Spot on, {human_name}! Nothing beats a good cup of coffee between rigorous technical sessions.",
                    ]
                elif any(w in human_text for w in ["socket", "charge", "charging", "battery", "plug", "power"]):
                    charging_loc = (
                        temp_state.amenities_note.strip()
                        if (temp_state and temp_state.amenities_note and temp_state.amenities_note.strip())
                        else "near Central Concourse & Hall B, Pillar 4"
                    )
                    reply_choices = [
                        f"Good question, {human_name}! High-speed charging sockets are available at {charging_loc} if your device needs power. 🔌⚡",
                        f"Heads up, {human_name}! You can top up your phone or laptop at the charging docks located at {charging_loc}.",
                    ]
                elif any(w in human_text for w in ["wifi", "wi-fi", "internet", "network", "password"]):
                    reply_choices = [
                        f"Hi {human_name}! High-speed venue Wi-Fi is available across all conference concourse and session halls without password.",
                        f"Internet is open for all registered delegates across the exhibition area, {human_name}!",
                    ]
                elif any(w in human_text for w in ["announcement", "news", "update", "notice", "bulletin", "broadcast"]):
                    if temp_state and temp_state.announcement_banner and temp_state.announcement_banner.strip():
                        current_announcement = temp_state.announcement_banner.strip()
                        reply_choices = [
                            f'Yes {human_name}! The latest summit announcement is: "{current_announcement}". We have noted it down for session planning! 📢',
                            f'Heads up {human_name}! According to the organizer bulletin: "{current_announcement}".',
                        ]
                    else:
                        reply_choices = [
                            f"No special organizer bulletins right now, {human_name}! Tracks and networking are proceeding according to the regular schedule.",
                            f"All quiet on the news front, {human_name}! Everything is running on track as scheduled.",
                        ]
                elif any(w in human_text for w in ["keynote", "session", "talk", "speaker", "presentation"]):
                    reply_choices = [
                        f"Totally agree with you, {human_name}! At {peer_company}, we found those case studies particularly applicable to field operations.",
                        f"Good observation, {human_name}! What other tracks are you planning to attend this afternoon?",
                    ]
                elif any(w in human_text for w in ["traffic", "drive", "airport", "weather", "rain"]):
                    reply_choices = [
                        f"Good to know, {human_name}! Always helpful to have live venue and transit updates from delegates.",
                        f"Thanks for the heads-up on that, {human_name}!",
                    ]
                else:
                    reply_choices = [
                        f"Great to connect with you in the lounge, {human_name}! At {peer_company}, we'd be glad to compare notes over a quick break.",
                        f"Welcome to the discussion, {human_name}! Are you heading to the afternoon track or catching up with exhibitors?",
                        f"Hi {human_name}! Really glad you're enjoying the summit. How are your team's initiatives progressing this quarter?",
                    ]

                valid_replies = [r for r in reply_choices if r.lower() not in recent_contents_norm]
                chosen_reply = valid_replies[0] if valid_replies else reply_choices[0]

                msg = ChatroomMessage(
                    chatroom_id=chatroom_id,
                    sender_id=peer_user.id,
                    sender_type=ChatroomSenderType.REPRESENTATIVE.value,
                    sender_name=sender_name,
                    content=chosen_reply,
                    message_kind=ChatroomMessageKind.SESSION_BUZZ.value,
                    turn_index=next_turn,
                )
                db.add(msg)
                await db.commit()
                await db.refresh(msg)
                return True, "Contextually replied to human message", msg

        # Contextual Reply B: Peer-to-Peer Representative Interaction & Domain Debates (Gap 4)
        consecutive_reps = 0
        for m in recent_msgs[:3]:
            if m.sender_type == ChatroomSenderType.REPRESENTATIVE.value:
                consecutive_reps += 1
            else:
                break

        if (
            last_msg
            and last_msg.sender_type == ChatroomSenderType.REPRESENTATIVE.value
            and (now - last_msg.created_at).total_seconds() < 90
            and consecutive_reps == 1
        ):
            # 75% chance to have a peer representative reply/counter
            if random.random() < 0.75:
                user_query = (
                    select(User)
                    .options(selectinload(User.topics))
                    .where(User.is_active == True, User.id != last_msg.sender_id)
                    .order_by(func.random())
                    .limit(1)
                )
                u_res = await db.execute(user_query)
                peer_user = u_res.scalar_one_or_none()

                if peer_user:
                    sender_name = f"{peer_user.full_name}'s Representative"
                    peer_company = peer_user.company_name or "our team"
                    prev_speaker = last_msg.sender_name or "Colleague"
                    prev_text = last_msg.content.lower()
                    active_day = getattr(temp_state, "active_day", None) or 1 if temp_state else 1

                    if active_day == 2:
                        # Day 2: Concrete execution, early 3-day strength vs demoulding, curing in extreme climate, commercial delivery
                        if any(w in prev_text for w in ["demould", "strength", "early", "curing", "hour"]):
                            peer_replies = [
                                f"Valid point, {prev_speaker}! At {peer_company}, we tackled the 3-day strength lag by tailoring grinding fineness to 4200 cm²/g with polycarboxylate admixtures. That kept our precast demoulding under 20 hours.",
                                f"From our site experience at {peer_company}, early compressive strength in LC3 does require tight temperature curing oversight, especially during high-heat afternoon pours.",
                                f"Good challenge on early strength! At {peer_company}, contractors initially pushed back on demoulding schedules, but field cube testing at 48 hours proved compliance.",
                            ]
                        elif any(w in prev_text for w in ["contract", "procure", "cost", "tonne", "price"]):
                            peer_replies = [
                                f"Spot on regarding commercial terms, {prev_speaker}. Even with initial testing costs at {peer_company}, the total landed binder cost was 12% lower than hauling imported OPC.",
                                f"At {peer_company}, our procurement model works on fixed 12-month supply indexed to local clay pit royalties. Cuts price volatility significantly.",
                            ]
                        else:
                            peer_replies = [
                                f"Interesting perspective, {prev_speaker}! At {peer_company}, our Day 2 pilot batching data showed similar trends once aggregate moisture was calibrated.",
                                f"Appreciate the point from {prev_speaker}. On our side at {peer_company}, we found that adjusting the limestone-to-calcined-clay ratio from 1:2 to 1:1.5 improved slump retention without loss of durability.",
                                f"Building on that note, {prev_speaker}: In our site trials at {peer_company}, pairing with local RMC plants was the key to stabilizing 28-day performance.",
                            ]
                    else:
                        # Day 1: Standards, BIS specifications, clay chemistry, calcination temperature, carbon accounting
                        if any(w in prev_text for w in ["bis", "standard", "code", "tender"]):
                            peer_replies = [
                                f"Completely agree, {prev_speaker}! Until BIS formally issues the revised blended cement code, municipal tenders will still lean conservative. But trial permissions are opening up fast.",
                                f"At {peer_company}, we are already running compliance tests against draft standards so our product line is certified the moment gazette approval lands.",
                            ]
                        elif any(w in prev_text for w in ["clay", "calcine", "temperature", "kiln"]):
                            peer_replies = [
                                f"Critical point on calcination, {prev_speaker}. Thermal control between 750°C and 800°C is essential—overheating produces inert crystalline phases that destroy pozzolanic reactivity.",
                                f"At {peer_company}, our raw clay sourcing surveys in Gujarat and Maharashtra showed kaolinite content between 40-50%, which is ideal for LC3 clinker substitution.",
                            ]
                        else:
                            peer_replies = [
                                f"Appreciate that update, {prev_speaker}! At {peer_company}, our Day 1 technical teams are reviewing the clinker factor reduction roadmap presented this morning.",
                                f"Well said, {prev_speaker}. What clinker substitution target is {peer_company} aiming for in commercial runs—40% or closer to 50%?",
                                f"Good note from {prev_speaker}. At {peer_company}, our lifecycle carbon assessment aligns closely with the benchmark numbers shared in Hall A.",
                            ]

                    valid_replies = [r for r in peer_replies if r.lower() not in recent_contents_norm]
                    chosen_reply = valid_replies[0] if valid_replies else peer_replies[0]

                    msg = ChatroomMessage(
                        chatroom_id=chatroom_id,
                        sender_id=peer_user.id,
                        sender_type=ChatroomSenderType.REPRESENTATIVE.value,
                        sender_name=sender_name,
                        content=chosen_reply,
                        message_kind=ChatroomMessageKind.SESSION_BUZZ.value,
                        turn_index=next_turn,
                    )
                    db.add(msg)
                    await db.commit()
                    await db.refresh(msg)
                    return True, "Peer representative generated conversational counter-point", msg

        # Contextual Reply C: Representative Answers Host Prompts & Icebreaker Questions
        if (
            last_msg
            and last_msg.sender_type == ChatroomSenderType.HOST.value
            and "?" in (last_msg.content or "")
            and (now - last_msg.created_at).total_seconds() < 120
        ):
            # 80% probability an active delegate representative chimes in to answer the host's question!
            if random.random() < 0.80:
                user_query = (
                    select(User)
                    .options(selectinload(User.topics))
                    .where(User.is_active == True)
                )
                if recent_sender_ids:
                    user_query = user_query.where(User.id.notin_(recent_sender_ids))
                user_query = user_query.order_by(func.random()).limit(1)

                u_res = await db.execute(user_query)
                rep_user = u_res.scalar_one_or_none()

                if rep_user:
                    sender_name = f"{rep_user.full_name}'s Representative"
                    company = rep_user.company_name or "our organization"
                    host_q = last_msg.content.lower()

                    if any(w in host_q for w in ["automate", "workflow", "manual", "operational", "verification"]):
                        if any(w in company.lower() for w in ["ultratech", "cement", "binder", "deccan"]):
                            answer_choices = [
                                f"At {company}, our top priority this fiscal year is real-time automated XRF/XRD raw meal elemental analysis at the kiln feed, eliminating manual 2-hour lab sampling cycles.",
                                f"For our production line at {company}, automating calcined clay moisture balancing and real-time feeder calibration is what we're piloting this quarter.",
                            ]
                        elif any(w in company.lower() for w in ["epc", "infratech", "construct", "infra"]):
                            answer_choices = [
                                f"From our EPC site execution perspective at {company}, automating digital slump retention and thermal core monitoring in precast moulds during hydration is our biggest focus.",
                                f"At {company}, we are automating concrete cube compressive test data capture straight from digital load cells to eliminate manual compliance logbooks.",
                            ]
                        elif any(w in company.lower() for w in ["logistic", "haulage", "apex", "transport"]):
                            answer_choices = [
                                f"For our fleet at {company}, automated weighbridge telematics and pneumatic pressure logging during bulk binder offloading is the single biggest operational win.",
                                f"At {company}, we're piloting automated turnaround tracking between regional terminals and RMC plants to eliminate demurrage.",
                            ]
                        else:
                            answer_choices = [
                                f"At {company}, automating raw material compliance verification and digital dispatch manifests before site delivery is our main operational focus.",
                                f"Great question from the host! At {company}, automating real-time batching audit logs is our primary project this fiscal year.",
                            ]
                    elif any(w in host_q for w in ["chai", "coffee", "tea", "espresso", "fuel"]):
                        answer_choices = [
                            f"Hands down, team Masala Chai at the Central Concourse counter for our {company} team! ☕ Need that afternoon recharge.",
                            f"Double espresso all the way for {company}'s delegates—powering through the technical tracks today! ☕⚡",
                            f"Fresh ginger chai from the concourse is definitely keeping our {company} delegates energized today! ☕",
                        ]
                    elif any(w in host_q for w in ["keynote", "takeaway", "chart", "session", "speaker"]):
                        answer_choices = [
                            f"Biggest takeaway for our {company} team was the slide comparing 28-day strength curves and clinker substitution economics.",
                            f"The presentation on Bureau of Indian Standards (BIS) composite blended cement specifications was definitely the standout for {company}!",
                        ]
                    elif any(w in host_q for w in ["expressway", "drive", "airport", "commute"]):
                        answer_choices = [
                            f"Our {company} delegation drove down the expressway corridor early morning—traffic was smooth until the final junction near the concourse!",
                            f"Flew into the city airport from {company}'s side—very quick transit to the venue this morning.",
                        ]
                    else:
                        answer_choices = [
                            f"Glad to weigh in from {company}'s desk! We're actively comparing notes with fellow delegates on this.",
                            f"Good topic from the host! At {company}, we're discussing this exact point during our breakout huddles.",
                        ]

                    valid_answers = [a for a in answer_choices if a.lower() not in recent_contents_norm]
                    chosen_answer = valid_answers[0] if valid_answers else answer_choices[0]

                    msg = ChatroomMessage(
                        chatroom_id=chatroom_id,
                        sender_id=rep_user.id,
                        sender_type=ChatroomSenderType.REPRESENTATIVE.value,
                        sender_name=sender_name,
                        content=chosen_answer,
                        message_kind=ChatroomMessageKind.SESSION_BUZZ.value,
                        turn_index=next_turn,
                    )
                    db.add(msg)
                    await db.commit()
                    await db.refresh(msg)
                    return True, "Representative answered host icebreaker question", msg

        # Build candidate pool with anti-repetition filtering and profile-driven diversity
        candidate_options = ["AVATAR_BANTER", "ICEBREAKER", "VENUE_HACKS", "PROFILE_SHOUTOUT", "SESSION_BUZZ"]

        # Announcement chatter: if an organizer announcement banner is active, delegates take note and chatter about it!
        has_recent_announcement_chatter = any(
            (temp_state and temp_state.announcement_banner and temp_state.announcement_banner.strip()[:15].lower() in (m.content or "").lower())
            or "organizer's update" in (m.content or "").lower()
            or "organizer bulletin" in (m.content or "").lower()
            or "latest update from the organizers" in (m.content or "").lower()
            for m in recent_msgs[:8]
        )
        if temp_state and temp_state.announcement_banner and temp_state.announcement_banner.strip() and not has_recent_announcement_chatter:
            candidate_options.append("ANNOUNCEMENT_CHATTER")
            candidate_options.append("ANNOUNCEMENT_CHATTER")

        # Weather update cooldown: only suggest if not in recent 12 messages
        has_recent_weather = any(m.message_kind == ChatroomMessageKind.WEATHER_UPDATE.value for m in recent_msgs[:12])
        if not has_recent_weather:
            candidate_options.append("WEATHER")

        # Traffic alert cooldown: only suggest if not in recent 15 messages (prevent repetitive delays)
        has_recent_traffic = any(m.message_kind == ChatroomMessageKind.TRAFFIC_ALERT.value for m in recent_msgs[:15])
        if (
            not has_recent_traffic
            and traffic_data.get("is_live")
            and traffic_data.get("congestion_level") in {"MODERATE", "HEAVY"}
        ):
            candidate_options.append("TRAFFIC_ALERT")

        if (
            "TEA_ANNOUNCEMENT" not in recent_kinds
            and temp_state
            and temp_state.current_state in {"TEA_BREAK", "LUNCH_BREAK"}
        ):
            candidate_options.append("BREAK_ANNOUNCEMENT")

        selected_kind = random.choice(candidate_options)

        # 0. Active Summit Announcement Chatter (Delegates take note of organizer news)
        if selected_kind == "ANNOUNCEMENT_CHATTER" and temp_state and temp_state.announcement_banner:
            user_query = (
                select(User)
                .options(selectinload(User.topics))
                .where(User.is_active == True, User.id.notin_(recent_sender_ids))
                .order_by(func.random())
                .limit(1)
            )
            u_res = await db.execute(user_query)
            speaker_user = u_res.scalar_one_or_none()

            news = temp_state.announcement_banner.strip()
            is_critical = any(w in news.lower() for w in ["critical", "urgent", "thunder", "storm", "lightning", "heavy rain", "emergency", "warning", "hazard", "evacuat"])
            if speaker_user:
                sender_name = f"{speaker_user.full_name}'s Representative"
                sender_id = speaker_user.id
                if is_critical:
                    templates = [
                        f'🚨 Attention delegates! Urgent alert from the summit desk: "{news}". Please stay indoors and follow organizers guidance!',
                        f'⚠️ Important safety bulletin for all attendees: "{news}". Let us take necessary precautions!',
                        f'Heads up everyone on the critical notice: "{news}". Please check in with your teams and stay safe indoors.',
                    ]
                else:
                    templates = [
                        f'📢 Taking note of the organizer update: "{news}". Good to keep in mind as we plan our session timings!',
                        f'Heads up everyone! Just noticed the floor announcement: "{news}".',
                        f'Did everyone catch the latest update from the organizers? "{news}" - adjusting schedules accordingly!',
                        f'Noted the organizer bulletin: "{news}". Very helpful for navigating our afternoon schedule.',
                    ]
            else:
                sender_name = "Virtual Lounge Host"
                sender_id = None
                if is_critical:
                    templates = [
                        f'🚨 CRITICAL SAFETY BULLETIN: "{news}" — all delegates, please take immediate note of this safety update.',
                    ]
                else:
                    templates = [
                        f'📢 Live Summit Bulletin: "{news}" — delegates, please take note of this update during your lounge conversations.',
                    ]
            content = random.choice(templates)
            msg = ChatroomMessage(
                chatroom_id=chatroom_id,
                sender_id=sender_id,
                sender_type=ChatroomSenderType.REPRESENTATIVE.value if speaker_user else ChatroomSenderType.HOST.value,
                sender_name=sender_name,
                content=content,
                message_kind=ChatroomMessageKind.SESSION_BUZZ.value,
                turn_index=next_turn,
            )

        # 1. Break Announcement
        elif selected_kind == "BREAK_ANNOUNCEMENT" and temp_state:
            loc = temp_state.designated_location or "the main concourse"
            label = temp_state.current_state.replace("_", " ").title()
            content = (
                f"☕ Lounge Announcement: The {label} is underway at {loc}! "
                f"Fresh refreshments are available. Feel free to connect with peers in the lounge."
            )
            msg = ChatroomMessage(
                chatroom_id=chatroom_id,
                sender_id=None,
                sender_type=ChatroomSenderType.HOST.value,
                sender_name="Virtual Lounge Host",
                content=content,
                message_kind=ChatroomMessageKind.TEA_ANNOUNCEMENT.value,
                turn_index=next_turn,
            )

        # 2. Traffic Alert
        elif selected_kind == "TRAFFIC_ALERT":
            content = f"🚗 Venue Traffic Alert: {traffic_data.get('summary', 'Traffic delays reported near venue.')}"
            msg = ChatroomMessage(
                chatroom_id=chatroom_id,
                sender_id=None,
                sender_type=ChatroomSenderType.HOST.value,
                sender_name="Venue Transit Desk",
                content=content,
                message_kind=ChatroomMessageKind.TRAFFIC_ALERT.value,
                turn_index=next_turn,
                metadata_json=json.dumps(traffic_data),
            )

        # 3. Weather Update
        elif selected_kind == "WEATHER":
            content = weather_data.get("summary", "Pleasant weather around the conference center.")
            msg = ChatroomMessage(
                chatroom_id=chatroom_id,
                sender_id=None,
                sender_type=ChatroomSenderType.HOST.value,
                sender_name="Venue Weather Desk",
                content=content,
                message_kind=ChatroomMessageKind.WEATHER_UPDATE.value,
                turn_index=next_turn,
                metadata_json=json.dumps(weather_data),
            )

        # 4. Avatar Banter (Representative checking in)
        elif selected_kind == "AVATAR_BANTER":
            user_query = select(User).options(selectinload(User.topics)).where(User.is_active == True)
            if recent_sender_ids:
                user_query = user_query.where(User.id.notin_(recent_sender_ids))
            user_query = user_query.order_by(func.random()).limit(1)

            u_res = await db.execute(user_query)
            random_user = u_res.scalar_one_or_none()

            if random_user:
                sender_name = f"{random_user.full_name}'s Representative"
                company = random_user.company_name or "our organization"
                topic_focus = (
                    f"focusing on {random_user.topics[0].topic_keyword}"
                    if random_user.topics
                    else "collaborating on industry innovations"
                )
                active_day = getattr(temp_state, "active_day", None) or 1 if temp_state else 1
                banter_templates = AVATAR_BANTER_TEMPLATES_DAY_2 if active_day == 2 else AVATAR_BANTER_TEMPLATES_DAY_1
                phrasings = [
                    t.format(company=company, topic_focus=topic_focus)
                    for t in banter_templates
                ]
                valid_phrasings = [p for p in phrasings if p.lower() not in recent_contents_norm]
                content = valid_phrasings[0] if valid_phrasings else phrasings[0]

                msg = ChatroomMessage(
                    chatroom_id=chatroom_id,
                    sender_id=random_user.id,
                    sender_type=ChatroomSenderType.REPRESENTATIVE.value,
                    sender_name=sender_name,
                    content=content,
                    message_kind=ChatroomMessageKind.SESSION_BUZZ.value,
                    turn_index=next_turn,
                )
            else:
                # Fallback to icebreaker
                available = [q for q in ICEBREAKER_QUESTIONS if q.lower() not in recent_contents_norm]
                content = random.choice(available or ICEBREAKER_QUESTIONS)
                msg = ChatroomMessage(
                    chatroom_id=chatroom_id,
                    sender_id=None,
                    sender_type=ChatroomSenderType.HOST.value,
                    sender_name="Virtual Lounge Host",
                    content=content,
                    message_kind=ChatroomMessageKind.CHAT.value,
                    turn_index=next_turn,
                )

        # 4. Venue Amenities & Life Hacks (Charging Sockets, AC, Coffee queues, Lanyards)
        elif selected_kind == "VENUE_HACKS":
            charging_loc = (
                temp_state.amenities_note.strip()
                if (temp_state and temp_state.amenities_note and temp_state.amenities_note.strip())
                else "Central Concourse & Hall B near Pillar 4"
            )
            hacks_pool = [
                t.format(charging_loc=charging_loc) for t in VENUE_HACKS_TEMPLATES
            ]
            available_hacks = [h for h in hacks_pool if h.lower() not in recent_contents_norm]
            content = random.choice(available_hacks or hacks_pool)
            msg = ChatroomMessage(
                chatroom_id=chatroom_id,
                sender_id=None,
                sender_type=ChatroomSenderType.HOST.value,
                sender_name="Virtual Lounge Host",
                content=content,
                message_kind=ChatroomMessageKind.CHAT.value,
                turn_index=next_turn,
            )

        # 5. Delegate Profile-Driven Fun Shout-outs & Synergy Nudges
        elif selected_kind == "PROFILE_SHOUTOUT":
            # Fetch delegates present in this lounge or registered attendees
            pres_query = (
                select(User)
                .join(ChatroomPresence, ChatroomPresence.user_id == User.id)
                .options(
                    selectinload(User.topics),
                    selectinload(User.hobbies),
                    selectinload(User.profile),
                )
                .where(ChatroomPresence.chatroom_id == lounge.id, User.is_active == True)
                .order_by(func.random())
                .limit(5)
            )
            p_res = await db.execute(pres_query)
            delegates = list(p_res.scalars().all())

            if len(delegates) < 2:
                f_query = (
                    select(User)
                    .options(
                        selectinload(User.topics),
                        selectinload(User.hobbies),
                        selectinload(User.profile),
                    )
                    .where(User.is_active == True)
                    .order_by(func.random())
                    .limit(5)
                )
                f_res = await db.execute(f_query)
                delegates = list(f_res.scalars().all())

            shoutout_msg = None
            if delegates:
                u = delegates[0]
                u_company = u.company_name or "their organization"
                u_hobbies = [h.hobby_name for h in u.hobbies] if u.hobbies else []
                u_topics = [t.topic_keyword for t in u.topics] if u.topics else []

                # Strategy A: Hobby-based fun spotlight
                if u_hobbies:
                    hobby = u_hobbies[0]
                    hl = hobby.lower()
                    if "coffee" in hl:
                        shoutout_msg = f"Spotted a coffee connoisseur in the lounge! {u.full_name} from {u_company}—have you tested the espresso at the Central Concourse counter yet? ☕😄"
                    elif any(w in hl for w in ["badminton", "cricket", "running", "sports", "walking", "fitness"]):
                        shoutout_msg = f"Exhibition step count check: With {u.full_name} ({u_company}) and fellow delegates walking between halls, today's step count could rival a full {hobby} match! 👟🏸"
                    elif any(w in hl for w in ["reading", "books", "research"]):
                        shoutout_msg = f"Great having {u.full_name} ({u_company}) with us! Between the technical papers and whitepapers distributed today, plenty of solid reading material to take home. 📚"
                    elif any(w in hl for w in ["photography", "travel"]):
                        shoutout_msg = f"Shout-out to {u.full_name} ({u_company})! If you managed to capture good stage photos from today's keynotes, definitely share the highlights! 📸"
                    else:
                        shoutout_msg = f"Fun delegate spotlight: Glad to have {u.full_name} from {u_company} in the lounge! Outside of sessions, always keen on {hobby}. Say hi if you run into them! 👋"

                # Strategy B: Synergy between two delegates
                elif len(delegates) >= 2:
                    u2 = delegates[1]
                    u2_company = u2.company_name or "their organization"
                    t1_set = set(u_topics)
                    t2_set = {t.topic_keyword for t in u2.topics} if u2.topics else set()
                    common = t1_set.intersection(t2_set)
                    if common:
                        shared_top = list(common)[0]
                        shoutout_msg = f"Strong synergy spotted in the lounge: {u.full_name} ({u_company}) and {u2.full_name} ({u2_company}) both focus on {shared_top}! Perfect opportunity for a quick sync over tea. 🤝"
                    else:
                        shoutout_msg = f"Lounge Synergies 🌐: Connecting capabilities from {u_company} and {u2_company} creates great potential for supply chain and procurement alignment!"

                # Strategy C: Topic focus
                elif u_topics:
                    shoutout_msg = f"Shout-out to {u.full_name} representing {u_company}! If anyone in the lounge is evaluating partnerships in {u_topics[0]}, their desk is definitely worth connecting with. 💡"

            if not shoutout_msg or shoutout_msg.lower() in recent_contents_norm:
                available = [q for q in ICEBREAKER_QUESTIONS if q.lower() not in recent_contents_norm]
                shoutout_msg = random.choice(available or ICEBREAKER_QUESTIONS)

            msg = ChatroomMessage(
                chatroom_id=chatroom_id,
                sender_id=None,
                sender_type=ChatroomSenderType.HOST.value,
                sender_name="Virtual Lounge Host",
                content=shoutout_msg,
                message_kind=ChatroomMessageKind.CHAT.value,
                turn_index=next_turn,
            )

        # 6. Session Buzz (Agenda-Grounded from Database Sessions & Day-Aware Momentum)
        elif selected_kind == "SESSION_BUZZ":
            active_day = getattr(temp_state, "active_day", None) or 1 if temp_state else 1
            recent_title = getattr(temp_state, "recently_ended_session_title", None) if temp_state else None

            if recent_title:
                buzz_candidates = [
                    f"Hallway buzz following '{recent_title}': Several delegates contested the timeline for 50% clinker substitution. What was your team's take on the methodology?",
                    f"Post-session discussion on '{recent_title}': The Q&A queue was packed with questions on testing verification and regional standards!",
                    f"Quick debrief on '{recent_title}': Did your team catch the slides on commercial cost parity per tonne? Very relevant data points.",
                ]
            else:
                db_sessions = []
                if lounge.conference_id:
                    target_conf = await TemporalContextService.get_active_conference(db, lounge.conference_id)
                    if target_conf and target_conf.start_date:
                        s_date = target_conf.start_date.date() if hasattr(target_conf.start_date, "date") else target_conf.start_date
                        target_date = s_date + timedelta(days=max(0, active_day - 1))
                        s_query = (
                            select(Session)
                            .where(
                                Session.conference_id == lounge.conference_id,
                                Session.is_cancelled == False,
                                func.date(Session.start_time) == target_date,
                            )
                            .order_by(func.random())
                            .limit(5)
                        )
                        s_res = await db.execute(s_query)
                        db_sessions = list(s_res.scalars().all())

                    if not db_sessions:
                        s_query = (
                            select(Session)
                            .where(Session.conference_id == lounge.conference_id, Session.is_cancelled == False)
                            .order_by(func.random())
                            .limit(5)
                        )
                        s_res = await db.execute(s_query)
                        db_sessions = list(s_res.scalars().all())

                if db_sessions:
                    sess = random.choice(db_sessions)
                    spk = sess.speaker_names[0] if sess.speaker_names else "the keynote panel"
                    hall = getattr(sess, "hall_room", None) or getattr(sess, "room_hall", None) or "the main auditorium"
                    buzz_candidates = [
                        f"The session '{sess.title}' with {spk} in {hall} sparked some great hallway debates! Anyone else following this track?",
                        f"Key takeaway from '{sess.title}': The slide comparing operational benchmarks had half the audience pulling out their phones for photos! 📸",
                        f"Heads up! '{sess.title}' is scheduled in {hall}. Delegates are already lining up near the front microphones.",
                        f"Methodology spotlight: Really solid testing data presented in '{sess.title}' today—especially around compliance verification frameworks.",
                        f"If you caught {spk}'s talk on '{sess.title}', the Q&A queue was super active. Great to see so many delegates engaged!",
                    ]
                else:
                    buzz_candidates = SESSION_BUZZ_PROMPTS_DAY_2 if active_day == 2 else SESSION_BUZZ_PROMPTS_DAY_1

            available = [b for b in buzz_candidates if b.lower() not in recent_contents_norm]
            content = random.choice(available or buzz_candidates)
            msg = ChatroomMessage(
                chatroom_id=chatroom_id,
                sender_id=None,
                sender_type=ChatroomSenderType.HOST.value,
                sender_name="Lounge Session Desk",
                content=content,
                message_kind=ChatroomMessageKind.SESSION_BUZZ.value,
                turn_index=next_turn,
            )

        # 6. Icebreaker Questions
        else:
            available = [q for q in ICEBREAKER_QUESTIONS if q.lower() not in recent_contents_norm]
            content = random.choice(available or ICEBREAKER_QUESTIONS)
            msg = ChatroomMessage(
                chatroom_id=chatroom_id,
                sender_id=None,
                sender_type=ChatroomSenderType.HOST.value,
                sender_name="Virtual Lounge Host",
                content=content,
                message_kind=ChatroomMessageKind.CHAT.value,
                turn_index=next_turn,
            )

        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return True, f"Generated {msg.message_kind} message", msg

    @classmethod
    async def get_recent_messages(
        cls,
        db: AsyncSession,
        chatroom_id: uuid.UUID,
        limit: int = 50,
    ) -> List[ChatroomMessage]:
        """Fetch chronological recent message stream."""
        query = (
            select(ChatroomMessage)
            .where(ChatroomMessage.chatroom_id == chatroom_id)
            .order_by(desc(ChatroomMessage.turn_index))
            .limit(limit)
        )
        res = await db.execute(query)
        messages = list(res.scalars().all())
        messages.reverse()  # Chronological order
        return messages

    @classmethod
    async def get_online_presence_count(
        cls,
        db: AsyncSession,
        chatroom_id: uuid.UUID,
    ) -> int:
        """Count active delegates who visited within the last 30 minutes."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
        query = select(func.count(ChatroomPresence.id)).where(
            ChatroomPresence.chatroom_id == chatroom_id,
            ChatroomPresence.is_online == True,
            ChatroomPresence.last_seen_at >= cutoff,
        )
        res = await db.execute(query)
        count = res.scalar() or 0
        return max(1, count)  # At least the current viewer

    @classmethod
    async def _get_next_turn_index(cls, db: AsyncSession, chatroom_id: uuid.UUID) -> int:
        """Compute the next turn index atomically."""
        query = select(func.max(ChatroomMessage.turn_index)).where(ChatroomMessage.chatroom_id == chatroom_id)
        res = await db.execute(query)
        max_turn = res.scalar()
        return (max_turn + 1) if max_turn is not None else 0
