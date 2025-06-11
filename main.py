import json
import streamlit as st
import pandas as pd
from streamlit_cookies_controller import CookieController
from streamlit_option_menu import option_menu

st.set_page_config(page_title="RHS Gradebook & Final Goal Calculator", layout="wide")
controller = CookieController()

stored = controller.get("grade_data")
if stored:
    if isinstance(stored, (str, bytes)):
        try:
            loaded = json.loads(stored)
        except json.JSONDecodeError:
            loaded = {}
    elif isinstance(stored, dict):
        loaded = stored
    else:
        loaded = {}
    grade_data = {}
    for k, v in loaded.items():
        try:
            grade_data[int(k)] = v
        except ValueError:
            pass
    for g in [9, 10, 11, 12]:
        grade_data.setdefault(g, {})
else:
    grade_data = {g: {} for g in [9, 10, 11, 12]}

st.session_state.grade_data = grade_data

def percent_to_letter(p):
    if p >= 97: return "A+"
    if p >= 93: return "A"
    if p >= 90: return "A-"
    if p >= 87: return "B+"
    if p >= 83: return "B"
    if p >= 80: return "B-"
    if p >= 77: return "C+"
    if p >= 73: return "C"
    if p >= 70: return "C-"
    if p >= 67: return "D+"
    if p >= 63: return "D"
    if p >= 60: return "D-"
    return "F"

def required_final(mp_avg, target):
    return (target - 0.9 * mp_avg) / 0.1

with st.sidebar:
    selected = option_menu(
        menu_title=None,
        options=["Final Goal Calculator", "Gradebook"],
        icons=["calculator-fill", "book-fill"],
        menu_icon="app-indicator",
        default_index=0,
        orientation="vertical",
        styles={
            "nav-link":        {"font-size": "16px", "text-align": "left", "color": "#3d3a2a"},
            "nav-link-selected": {"background-color": "#fafafa", "color": "#3d3a2a"},
        }
    )

if selected == "Final Goal Calculator":
    st.title("🎯 RHS Final Goal Calculator")
    grade_level = st.selectbox("Grade level", [9, 10, 11, 12])
    courses     = list(st.session_state.grade_data[grade_level].keys())
    if not courses:
        st.info("No courses found. Please add courses on the Gradebook page.")
        st.stop()

    course = st.selectbox("Select course", courses)
    entry  = st.session_state.grade_data[grade_level][course]

    st.subheader("Marking Period Scores")
    cols_inp = st.columns(4)
    mp_inputs = {}
    for idx, mp in enumerate(["MP1", "MP2", "MP3", "MP4"]):
        default = entry.get(mp)
        chk_key = f"include_{grade_level}_{course}_{mp}"
        inp_key = f"input_{grade_level}_{course}_{mp}"
        with cols_inp[idx]:
            use_mp = st.checkbox(f"Use {mp}", value=(default is None), key=chk_key)
            val = st.number_input(
                f"{mp} %",
                min_value=0.0, max_value=100.0,
                value=float(default) if default is not None else 0.0,
                step=0.1,
                disabled=not use_mp,
                key=inp_key
            )
        mp_inputs[mp] = val if use_mp else None

    valid = [v for v in mp_inputs.values() if v is not None]
    if valid:
        mp_avg = sum(valid) / len(valid)
        st.write(f"**MP average:** {mp_avg:.2f}% ({percent_to_letter(mp_avg)})")
    else:
        mp_avg = 0.0
        st.write("**MP average:** NA (no MP selected)")

    base_thresholds = {
        "A+": 97, "A": 93, "A-": 90,
        "B+": 87, "B": 83, "B-": 80,
        "C+": 77, "C": 73, "C-": 70,
        "D+": 67, "D": 63, "D-": 60,
        "F":   0
    }
    thresholds = {
        k: (v - 0.5 if k != "F" else 0)
        for k, v in base_thresholds.items()
    }

    goal = st.selectbox("Goal final grade", list(thresholds.keys()), index=0)
    req  = required_final(mp_avg, thresholds[goal])
    st.write(f"To hit **{goal}**, you need **{req:.2f}%** on the final exam")

    if st.button("Save Grades"):
        st.session_state.grade_data[grade_level][course] = {
            **mp_inputs,
            "Final":     entry.get("Final"),
            "Goal":      goal,
            "Required":  req
        }
        controller.set("grade_data", json.dumps(st.session_state.grade_data))
        st.success("Grades & goal saved!")

else:
    st.title("📚 Gradebook")
    grade_level = st.selectbox("Select grade level", [9, 10, 11, 12])
    new_course  = st.text_input("➕ New course name")
    if st.button("Add course") and new_course:
        if new_course not in st.session_state.grade_data[grade_level]:
            st.session_state.grade_data[grade_level][new_course] = {
                "MP1": None, "MP2": None, "MP3": None, "MP4": None,
                "Final": None, "Goal": None, "Required": None
            }
            controller.set("grade_data", json.dumps(st.session_state.grade_data))
            st.success(f"Added course '{new_course}'")
        else:
            st.error("Course already exists")

    courses = st.session_state.grade_data[grade_level]
    if courses:
        rows = []
        for c, vals in courses.items():
            row = {"Course": c}
            filled = []
            for i in range(1,5):
                v = vals.get(f"MP{i}")
                if v is None:
                    row[f"MP{i}"] = "NA"
                else:
                    row[f"MP{i}"] = f"{v:.1f}% ({percent_to_letter(v)})"
                    filled.append(v)
            if filled:
                avg = sum(filled)/len(filled)
                row["MP Avg"] = f"{avg:.1f}% ({percent_to_letter(avg)})"
            else:
                avg = None
                row["MP Avg"] = "NA"

            final = vals.get("Final")
            if final is None:
                row["Final Exam"]  = "NA"
                row["Final Grade"] = "NA"
            else:
                row["Final Exam"]  = f"{final:.1f}% ({percent_to_letter(final)})"
                overall = 0.9 * (avg or 0) + 0.1 * final
                row["Final Grade"] = f"{overall:.1f}% ({percent_to_letter(overall)})"

            row["Goal"]     = vals.get("Goal") or "NA"
            req_val = vals.get("Required")
            row["Req Final"] = f"{req_val:.1f}%" if req_val is not None else "NA"
            rows.append(row)

        display_cols = [
            "Course","MP1","MP2","MP3","MP4",
            "MP Avg","Goal","Req Final","Final Exam","Final Grade","Remove"
        ]
        widths = [2] + [1]*(len(display_cols)-1)

        hdr = st.columns(widths)
        for i, col in enumerate(display_cols):
            hdr[i].markdown(f"**{col}**")

        for row in rows:
            cols = st.columns(widths)
            for i, fld in enumerate(display_cols[:-1]):
                cols[i].write(row[fld])
            name = row["Course"]
            if cols[-1].button("🗑️", key=f"rm_{grade_level}_{name}"):
                st.session_state.grade_data[grade_level].pop(name, None)
                controller.set("grade_data", json.dumps(st.session_state.grade_data))
                st.rerun()

        st.markdown("---")
        st.subheader("Add / Update Final Exam Results")
        course_for_final = st.selectbox("Which course?", list(courses.keys()))
        current = courses[course_for_final].get("Final")
        new_final = st.number_input(
            "Final Exam %", 0.0, 100.0,
            value=current or 0.0, step=0.1
        )
        if st.button("Save Final Score"):
            st.session_state.grade_data[grade_level][course_for_final]["Final"] = new_final
            controller.set("grade_data", json.dumps(st.session_state.grade_data))
            st.success(f"Saved final exam for {course_for_final}")

    else:
        st.info("No courses added yet")

def add_footer():
    st.markdown("""
    <style>
      footer {visibility: hidden;}
      .custom-footer {
        position: fixed; bottom: 0; width: 100%;
        text-align: center; font-size:12px; color:#3d3a2a;
        padding:4px 0; background:transparent;
      }
    </style>
    <div class="custom-footer">
      Made by Shloak Vatsyayan
    </div>
    """, unsafe_allow_html=True)

add_footer()
