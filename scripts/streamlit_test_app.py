from __future__ import annotations

import json
from typing import Any

import httpx
import streamlit as st


DEFAULT_API_URL = "http://127.0.0.1:8000"


def init_state() -> None:
    st.session_state.setdefault("api_url", DEFAULT_API_URL)
    st.session_state.setdefault("access_token", "")
    st.session_state.setdefault("refresh_token", "")
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("conversation_id", "")


def api_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
    return headers


def api_url(path: str) -> str:
    return f"{st.session_state.api_url.rstrip('/')}{path}"


def request_json(method: str, path: str, **kwargs: Any) -> tuple[int, Any]:
    try:
        response = httpx.request(
            method,
            api_url(path),
            headers=api_headers(),
            timeout=30,
            **kwargs,
        )
        try:
            return response.status_code, response.json()
        except json.JSONDecodeError:
            return response.status_code, response.text
    except Exception as exc:
        return 0, {"error": str(exc)}


def require_auth() -> bool:
    if not st.session_state.access_token:
        st.warning("Login first.")
        return False
    return True


def login_panel() -> None:
    st.subheader("Auth")
    email = st.text_input("Email", value="omar.elfassi@n7chat.local")
    password = st.text_input("Password", value="dev-password-hash-change-me", type="password")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Login", use_container_width=True):
            status_code, data = request_json(
                "POST",
                "/auth/login",
                json={"email": email, "password": password},
            )
            if status_code == 200:
                st.session_state.access_token = data["access_token"]
                st.session_state.refresh_token = data["refresh_token"]
                st.success("Logged in.")
            else:
                st.error(data)

    with col2:
        if st.button("Refresh", use_container_width=True):
            status_code, data = request_json(
                "POST",
                "/auth/refresh",
                json={"refresh_token": st.session_state.refresh_token},
            )
            if status_code == 200:
                st.session_state.access_token = data["access_token"]
                st.session_state.refresh_token = data["refresh_token"]
                st.success("Token rotated.")
            else:
                st.error(data)

    with col3:
        if st.button("Logout", use_container_width=True):
            if st.session_state.refresh_token:
                request_json(
                    "POST",
                    "/auth/logout",
                    json={"refresh_token": st.session_state.refresh_token},
                )
            st.session_state.access_token = ""
            st.session_state.refresh_token = ""
            st.session_state.user = None
            st.session_state.conversation_id = ""
            st.success("Logged out.")

    if st.session_state.access_token:
        st.caption("Access token is stored in Streamlit session state.")


def profile_page() -> None:
    st.subheader("Profile")
    if not require_auth():
        return

    if st.button("Load /profile/me"):
        status_code, data = request_json("GET", "/profile/me")
        if status_code == 200:
            st.session_state.user = data
            st.success("Profile loaded.")
        else:
            st.error(data)

    if st.session_state.user:
        st.json(st.session_state.user)
        role = st.session_state.user.get("role")
        st.info(f"Current role: {role}")

    st.divider()
    st.markdown("Profile photo upload")
    photo = st.file_uploader("Photo", type=["png", "jpg", "jpeg", "webp"])
    if st.button("Upload photo") and photo:
        upload_file("/profile/photo", photo)


def chat_page() -> None:
    st.subheader("Chat")
    if not require_auth():
        return

    title = st.text_input("Conversation title", value="Streamlit test")
    if st.button("Create conversation"):
        status_code, data = request_json(
            "POST",
            "/chat/conversations",
            json={"title": title},
        )
        if status_code == 201:
            st.session_state.conversation_id = data["id"]
            st.success(f"Conversation: {data['id']}")
        else:
            st.error(data)

    st.session_state.conversation_id = st.text_input(
        "Conversation ID",
        value=st.session_state.conversation_id,
    )
    message = st.text_area("Message", value="donne moi mes notes")

    if st.button("Send streamed message"):
        if not st.session_state.conversation_id:
            st.error("Create or paste a conversation ID first.")
            return

        output = st.empty()
        collected = ""
        try:
            with httpx.stream(
                "POST",
                api_url("/chat/stream"),
                headers=api_headers(),
                json={
                    "conversation_id": st.session_state.conversation_id,
                    "message": message,
                },
                timeout=120,
            ) as response:
                if response.status_code != 200:
                    st.error(response.read().decode("utf-8", errors="replace"))
                    return
                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    payload = line.removeprefix("data: ")
                    if payload == "[DONE]":
                        break
                    event = json.loads(payload)
                    collected += event.get("chunk", "")
                    if event.get("error"):
                        collected += f"\n\nERROR: {event['error']}"
                    output.markdown(collected)
        except Exception as exc:
            st.error(exc)


def courses_page() -> None:
    st.subheader("Courses")
    if not require_auth():
        return

    search = st.text_input("Search courses", value="")
    if st.button("List courses"):
        status_code, data = request_json(
            "GET",
            "/courses",
            params={"search": search or None, "limit": 50},
        )
        st.json(data if status_code == 200 else {"status": status_code, "data": data})

    st.divider()
    st.markdown("Teacher/admin course upload")
    course_file = st.file_uploader("Course file", type=["pdf", "docx", "ppt", "pptx", "txt"])
    if st.button("Upload course file") and course_file:
        upload_file("/courses/upload", course_file)

    st.divider()
    st.markdown("Create course row")
    module_id = st.text_input("Module ID")
    title = st.text_input("Title")
    description = st.text_area("Description")
    file_url = st.text_input("File URL from upload response")
    file_type = st.selectbox("File type", ["pdf", "docx", "ppt", "video", "link", "text"])
    if st.button("Create course"):
        status_code, data = request_json(
            "POST",
            "/courses",
            json={
                "module_id": module_id,
                "title": title,
                "description": description or None,
                "file_url": file_url or None,
                "file_type": file_type,
            },
        )
        st.json(data if status_code in (200, 201) else {"status": status_code, "data": data})


def events_page() -> None:
    st.subheader("Events")
    if not require_auth():
        return

    if st.button("List events"):
        status_code, data = request_json("GET", "/events", params={"upcoming_only": False})
        st.json(data if status_code == 200 else {"status": status_code, "data": data})

    st.divider()
    st.markdown("Create event")
    title = st.text_input("Event title")
    event_type = st.selectbox("Event type", ["exam", "conference", "holiday", "meeting"])
    start_date = st.text_input("Start date ISO", value="2026-06-01T09:00:00")
    end_date = st.text_input("End date ISO", value="")
    location = st.text_input("Location")
    notify_students = st.checkbox("Notify students", value=True)
    if st.button("Create event"):
        status_code, data = request_json(
            "POST",
            "/events",
            json={
                "title": title,
                "event_type": event_type,
                "start_date": start_date,
                "end_date": end_date or None,
                "location": location or None,
                "notify_students": notify_students,
            },
        )
        st.json(data if status_code in (200, 201) else {"status": status_code, "data": data})


def admin_documents_page() -> None:
    st.subheader("Admin Documents")
    if not require_auth():
        return

    doc = st.file_uploader("Administrative document", type=["pdf", "docx", "ppt", "pptx", "txt"])
    if st.button("Upload admin document") and doc:
        upload_file("/documents/upload", doc)


def upload_file(path: str, file_obj: Any) -> None:
    try:
        headers = {}
        if st.session_state.access_token:
            headers["Authorization"] = f"Bearer {st.session_state.access_token}"
        response = httpx.post(
            api_url(path),
            headers=headers,
            files={"file": (file_obj.name, file_obj.getvalue(), file_obj.type)},
            timeout=120,
        )
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = response.text
        if response.status_code in (200, 201):
            st.success("Uploaded.")
            st.json(data)
        else:
            st.error({"status": response.status_code, "data": data})
    except Exception as exc:
        st.error(exc)


def main() -> None:
    st.set_page_config(page_title="n7chat backend tester", layout="wide")
    init_state()

    st.title("n7chat Backend Tester")
    st.session_state.api_url = st.sidebar.text_input("API URL", value=st.session_state.api_url)
    page = st.sidebar.radio(
        "Page",
        ["Auth", "Profile", "Chat", "Courses", "Events", "Admin Documents"],
    )

    login_panel()
    st.divider()

    if page == "Auth":
        st.info("Use this page to login, refresh, and logout.")
    elif page == "Profile":
        profile_page()
    elif page == "Chat":
        chat_page()
    elif page == "Courses":
        courses_page()
    elif page == "Events":
        events_page()
    elif page == "Admin Documents":
        admin_documents_page()


if __name__ == "__main__":
    main()
