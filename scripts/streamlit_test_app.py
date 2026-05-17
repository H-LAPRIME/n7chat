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
        params: dict[str, Any] = {"limit": 50}
        if search.strip():
            params["search"] = search.strip()
        status_code, data = request_json(
            "GET",
            "/courses",
            params=params,
        )
        st.json(data if status_code == 200 else {"status": status_code, "data": data})

    st.divider()
    st.markdown("Teacher/admin course upload")
    if st.button("Load my modules for upload"):
        status_code, data = request_json("GET", "/courses/modules")
        if status_code == 200:
            st.session_state["course_modules"] = data
        else:
            st.error({"status": status_code, "data": data})
    if st.button("Load filieres for auto module"):
        status_code, data = request_json("GET", "/courses/filieres")
        if status_code == 200:
            st.session_state["course_filieres"] = data
        else:
            st.error({"status": status_code, "data": data})

    modules = st.session_state.get("course_modules", [])
    module_options = {
        f"{item.get('code')} - {item.get('name')} ({item.get('filiere_name')})": item.get("id")
        for item in modules
    }
    selected_module_label = st.selectbox(
        "Module for upload + embedding",
        [""] + list(module_options.keys()),
        key="upload_module_select",
    )
    upload_module_id = module_options.get(selected_module_label, "")
    manual_module_id = st.text_input("Existing Module ID, optional", value=upload_module_id, key="upload_module_id")

    filieres = st.session_state.get("course_filieres", [])
    filiere_options = {
        f"{item.get('code')} - {item.get('name')}": item.get("id")
        for item in filieres
    }
    selected_filiere_label = st.selectbox(
        "Filiere for auto-created module",
        [""] + list(filiere_options.keys()),
        key="upload_filiere_select",
    )
    upload_filiere_id = filiere_options.get(selected_filiere_label, "")
    manual_filiere_id = st.text_input("Or paste Filiere ID for auto-created module", value=upload_filiere_id)
    upload_module_name = st.text_input("Auto module name, optional")
    upload_module_code = st.text_input("Auto module code, optional")
    upload_semester = st.number_input("Auto module semester", min_value=1, step=1, value=1)
    upload_title = st.text_input("Course title for upload", key="upload_title")
    upload_description = st.text_area("Course description for upload", key="upload_description")
    course_file = st.file_uploader("Course file", type=["pdf", "docx", "ppt", "pptx", "txt"])
    if st.button("Upload course file") and course_file:
        fields = {}
        selected_module_id = manual_module_id.strip() or upload_module_id.strip()
        selected_filiere_id = manual_filiere_id.strip() or upload_filiere_id.strip()
        if selected_module_id:
            fields["module_id"] = selected_module_id
        elif selected_filiere_id:
            fields["filiere_id"] = selected_filiere_id
            fields["semester"] = str(int(upload_semester))
            if upload_module_name.strip():
                fields["module_name"] = upload_module_name.strip()
            if upload_module_code.strip():
                fields["module_code"] = upload_module_code.strip()
        else:
            st.error("Select an existing module or select/paste a filiere to auto-create one.")
            return
        if upload_title.strip():
            fields["title"] = upload_title.strip()
        if upload_description.strip():
            fields["description"] = upload_description.strip()
        upload_file("/courses/upload", course_file, fields=fields)

    st.divider()
    st.markdown("Create course row")
    module_id = st.text_input("Module ID")
    title = st.text_input("Title")
    description = st.text_area("Description")
    file_url = st.text_input("File URL from upload response")
    file_type = st.selectbox("File type", ["pdf", "docx", "ppt", "video", "link", "text"])
    if st.button("Create course"):
        if not module_id.strip():
            st.error("Module ID is required and must be a valid UUID.")
            return
        if not title.strip():
            st.error("Title is required.")
            return
        status_code, data = request_json(
            "POST",
            "/courses",
            json={
                "module_id": module_id.strip(),
                "title": title.strip(),
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
    doc_title = st.text_input("Document title")
    doc_description = st.text_area("Document description")
    if st.button("Upload admin document") and doc:
        fields = {}
        if doc_title.strip():
            fields["title"] = doc_title.strip()
        if doc_description.strip():
            fields["description"] = doc_description.strip()
        upload_file("/documents/upload", doc, fields=fields)


def admin_control_panel() -> None:
    st.subheader("Admin Control Panel")
    if not require_auth():
        return

    tab_overview, tab_users, tab_academic, tab_people, tab_assign = st.tabs(
        ["Overview", "Users", "Academic", "People", "Assignments"]
    )

    with tab_overview:
        if st.button("Load admin overview"):
            status_code, data = request_json("GET", "/admin/overview")
            st.json(data if status_code == 200 else {"status": status_code, "data": data})

    with tab_users:
        st.markdown("Create app user")
        email = st.text_input("User email", key="admin_user_email")
        password = st.text_input(
            "Initial password",
            value="dev-password-hash-change-me",
            type="password",
            key="admin_user_password",
        )
        role = st.selectbox("Role", ["student", "teacher", "admin"], key="admin_user_role")
        is_active = st.checkbox("Active", value=True, key="admin_user_active")
        if st.button("Create user"):
            status_code, data = request_json(
                "POST",
                "/admin/users",
                json={
                    "email": email,
                    "password": password,
                    "role": role,
                    "is_active": is_active,
                },
            )
            st.json(data if status_code == 201 else {"status": status_code, "data": data})

        if st.button("List users"):
            status_code, data = request_json("GET", "/admin/users")
            st.json(data if status_code == 200 else {"status": status_code, "data": data})

    with tab_academic:
        st.markdown("Create department")
        department_name = st.text_input("Department name")
        department_description = st.text_area("Department description")
        if st.button("Create department"):
            status_code, data = request_json(
                "POST",
                "/admin/departments",
                json={"name": department_name, "description": department_description or None},
            )
            st.json(data if status_code == 201 else {"status": status_code, "data": data})

        st.markdown("Create level")
        level_name = st.text_input("Level name", value="Licence 1")
        level_order = st.number_input("Level order", min_value=1, step=1, value=1)
        if st.button("Create level"):
            status_code, data = request_json(
                "POST",
                "/admin/levels",
                json={"name": level_name, "order_number": int(level_order)},
            )
            st.json(data if status_code == 201 else {"status": status_code, "data": data})

        st.markdown("Create filiere")
        filiere_department_id = st.text_input("Department ID for filiere")
        filiere_name = st.text_input("Filiere name")
        filiere_code = st.text_input("Filiere code")
        filiere_duration = st.number_input("Duration years", min_value=1, step=1, value=3)
        if st.button("Create filiere"):
            status_code, data = request_json(
                "POST",
                "/admin/filieres",
                json={
                    "department_id": filiere_department_id or None,
                    "name": filiere_name,
                    "code": filiere_code,
                    "duration_years": int(filiere_duration),
                },
            )
            st.json(data if status_code == 201 else {"status": status_code, "data": data})

        st.markdown("Create module")
        module_filiere_id = st.text_input("Module filiere ID")
        module_teacher_id = st.text_input("Optional teacher ID")
        module_name = st.text_input("Module name")
        module_code = st.text_input("Module code")
        module_semester = st.number_input("Semester", min_value=1, step=1, value=1)
        if st.button("Create module"):
            status_code, data = request_json(
                "POST",
                "/admin/modules",
                json={
                    "filiere_id": module_filiere_id,
                    "teacher_id": module_teacher_id or None,
                    "name": module_name,
                    "code": module_code,
                    "semester": int(module_semester),
                },
            )
            st.json(data if status_code == 201 else {"status": status_code, "data": data})

        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            if st.button("List departments"):
                st.json(request_json("GET", "/admin/departments")[1])
        with col_b:
            if st.button("List levels"):
                st.json(request_json("GET", "/admin/levels")[1])
        with col_c:
            if st.button("List filieres"):
                st.json(request_json("GET", "/admin/filieres")[1])
        with col_d:
            if st.button("List modules"):
                st.json(request_json("GET", "/admin/modules")[1])

    with tab_people:
        st.markdown("Create teacher profile for teacher user")
        teacher_user_id = st.text_input("Teacher user ID")
        teacher_code = st.text_input("Teacher code")
        teacher_first = st.text_input("Teacher first name")
        teacher_last = st.text_input("Teacher last name")
        teacher_dept = st.text_input("Teacher department ID")
        if st.button("Create teacher profile"):
            status_code, data = request_json(
                "POST",
                "/admin/teachers",
                json={
                    "user_id": teacher_user_id,
                    "teacher_code": teacher_code,
                    "first_name": teacher_first,
                    "last_name": teacher_last,
                    "department_id": teacher_dept or None,
                },
            )
            st.json(data if status_code == 201 else {"status": status_code, "data": data})

        st.markdown("Create student profile for student user")
        student_user_id = st.text_input("Student user ID")
        student_code = st.text_input("Student code")
        student_first = st.text_input("Student first name")
        student_last = st.text_input("Student last name")
        student_filiere = st.text_input("Initial filiere ID")
        student_level = st.text_input("Initial level ID")
        enrollment_year = st.number_input("Enrollment year", min_value=2000, step=1, value=2026)
        if st.button("Create student profile"):
            status_code, data = request_json(
                "POST",
                "/admin/students",
                json={
                    "user_id": student_user_id,
                    "student_code": student_code,
                    "first_name": student_first,
                    "last_name": student_last,
                    "filiere_id": student_filiere or None,
                    "level_id": student_level or None,
                    "enrollment_year": int(enrollment_year),
                },
            )
            st.json(data if status_code == 201 else {"status": status_code, "data": data})

        col1, col2 = st.columns(2)
        with col1:
            if st.button("List teachers"):
                st.json(request_json("GET", "/admin/teachers")[1])
        with col2:
            if st.button("List students"):
                st.json(request_json("GET", "/admin/students")[1])

    with tab_assign:
        st.markdown("Assign student to filiere / level")
        assign_student_id = st.text_input("Student ID to assign")
        assign_filiere_id = st.text_input("Assign filiere ID")
        assign_level_id = st.text_input("Assign level ID")
        assign_status = st.selectbox("Student status", ["", "active", "suspended", "graduated"])
        if st.button("Assign student"):
            payload: dict[str, Any] = {}
            if assign_filiere_id:
                payload["filiere_id"] = assign_filiere_id
            if assign_level_id:
                payload["level_id"] = assign_level_id
            if assign_status:
                payload["status"] = assign_status
            status_code, data = request_json(
                "PATCH",
                f"/admin/students/{assign_student_id}/assignment",
                json=payload,
            )
            st.json(data if status_code == 200 else {"status": status_code, "data": data})

        st.markdown("Assign teacher to module")
        assign_module_id = st.text_input("Module ID to assign")
        assign_teacher_id = st.text_input("Teacher ID, empty to unassign")
        if st.button("Assign teacher to module"):
            status_code, data = request_json(
                "PATCH",
                f"/admin/modules/{assign_module_id}/teacher",
                json={"teacher_id": assign_teacher_id or None},
            )
            st.json(data if status_code == 200 else {"status": status_code, "data": data})


def upload_file(path: str, file_obj: Any, fields: dict[str, str] | None = None) -> None:
    try:
        headers = {}
        if st.session_state.access_token:
            headers["Authorization"] = f"Bearer {st.session_state.access_token}"
        response = httpx.post(
            api_url(path),
            headers=headers,
            data=fields or {},
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
        ["Auth", "Profile", "Chat", "Courses", "Events", "Admin Documents", "Admin Control Panel"],
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
    elif page == "Admin Control Panel":
        admin_control_panel()


if __name__ == "__main__":
    main()
