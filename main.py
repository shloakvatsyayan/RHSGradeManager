import json
import streamlit as st
from streamlit_cookies_controller import CookieController
from streamlit_option_menu import option_menu
import pandas as pd

st.set_page_config(page_title="RHS Gradebook & Final Goal Calculator", layout="wide")

st.markdown("""
<style>
button.stButton > button {
  background: #bb5a38;
  border: none;
  border-radius: 8px;
  padding: 0.6rem 1.2rem;
  font-weight: 600;
  transition: background .2s ease;
}
button.stButton > button:hover {
  background: #d7694e;
}
[data-baseweb="checkbox"] {
  visibility: hidden;
  height: 0;
}
</style>
""", unsafe_allow_html=True)

controller = CookieController()
stored = controller.get("grade_data")
if stored:
    try:
        loaded = json.loads(stored) if isinstance(stored, (str, bytes)) else stored
    except:
        loaded = {}
    grade_data = {int(k): v for k, v in loaded.items() if k.isdigit()}
    for g in [9, 10, 11, 12]:
        grade_data.setdefault(g, {})
else:
    grade_data = {g: {} for g in [9, 10, 11, 12]}

st.session_state.grade_data = grade_data

def percent_to_letter(p):
    if p >= 96.5: return "A+"
    if p >= 92.5: return "A"
    if p >= 89.5: return "A-"
    if p >= 86.5: return "B+"
    if p >= 82.5: return "B"
    if p >= 79.5: return "B-"
    if p >= 76.5: return "C+"
    if p >= 72.5: return "C"
    if p >= 69.5: return "C-"
    if p >= 66.5: return "D+"
    if p >= 62.5: return "D"
    if p >= 59.5: return "D-"
    return "F"

def required_final(mp_avg, target):
    return (target - 0.9 * mp_avg) / 0.1

letter_to_cp = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "D-": 0.7,
    "F":  0.0
}

with st.sidebar:
    selected = option_menu(
        menu_title=None,
        options=["Final Goal Calculator", "Gradebook"],
        icons=["calculator-fill", "book-fill"],
        menu_icon="app-indicator",
        default_index=0,
        orientation="vertical",
        styles={
            "nav-link": {"font-size": "16px", "color": "#E6E6E6"},
            "nav-link-selected": {"background-color": "#2A2A2E", "color": "#bb5a38"},
            "container": {"padding": "1rem 0"}
        }
    )

if selected == "Final Goal Calculator":
    st.title("🎯 RHS Final Goal Calculator")
    grade_level = st.selectbox("Grade level", [9, 10, 11, 12])
    courses = list(st.session_state.grade_data[grade_level].keys())
    if not courses:
        st.info("No courses yet—add some on the Gradebook page.")
        st.stop()
    course = st.selectbox("Select course", courses)
    entry = st.session_state.grade_data[grade_level][course]
    cols = st.columns(4)
    mp_inputs = {}
    for i, mp in enumerate(["MP1", "MP2", "MP3", "MP4"]):
        chk_key = f"include_{grade_level}_{course}_{mp}"
        inp_key = f"input_{grade_level}_{course}_{mp}"
        with cols[i]:
            use_mp = st.toggle(label=f"Use {mp}", value=True, key=chk_key)
            val = st.number_input(
                f"{mp} %",
                min_value=0.0, max_value=100.0,
                value=float(entry.get(mp) or 0.0),
                step=0.1,
                disabled=not use_mp,
                key=inp_key
            )
        mp_inputs[mp] = val if use_mp else None
    valid = [v for v in mp_inputs.values() if v is not None]
    if valid:
        mp_avg = sum(valid) / len(valid)
        st.write(f"**MP average:** {mp_avg:.2f}% ({percent_to_letter(mp_avg)})")
        base_thr = {
            "A+": 97, "A": 93, "A-": 90,
            "B+": 87, "B": 83, "B-": 80,
            "C+": 77, "C": 73, "C-": 70,
            "D+": 67, "D": 63, "D-": 60,
            "F":  0
        }
        thresholds = {k: (v - 0.5 if k != "F" else 0) for k, v in base_thr.items()}
        goal = st.selectbox("Goal final grade", list(thresholds.keys()), index=0)
        req = required_final(mp_avg, thresholds[goal])
        st.write(f"To hit **{goal}**, you need **{req:.2f}%** on the final exam")
    else:
        st.write("**MP average:** NA")
        st.info("Select at least one marking period.")
    if st.button("Save Grades"):
        st.session_state.grade_data[grade_level][course] = {
            **mp_inputs,
            "Final": entry.get("Final"),
            "Goal": goal if valid else None,
            "Required": req if valid else None,
            "Credits": entry.get("Credits", 1.0),
            "Type": entry.get("Type", "CP")
        }
        controller.set("grade_data", json.dumps(st.session_state.grade_data))
        st.success("✅ Grades & goal saved!")
else:
    st.title("📚 Gradebook")
    grade_level = st.selectbox("Select grade level", [9, 10, 11, 12])
    new_course = st.text_input("➕ New course name", key=f"new_course_{grade_level}")
    course_type = st.selectbox("Course type", ["CP", "Honors", "AP"], key=f"type_{grade_level}")
    new_credits = st.number_input("Course credits", 0.5, 5.0, 1.0, 0.5, key=f"credits_{grade_level}")
    if st.button("Add course") and new_course:
        if new_course not in st.session_state.grade_data[grade_level]:
            st.session_state.grade_data[grade_level][new_course] = {
                "MP1": None, "MP2": None, "MP3": None, "MP4": None,
                "Final": None, "Goal": None, "Required": None,
                "Credits": new_credits,
                "Type": course_type
            }
            controller.set("grade_data", json.dumps(st.session_state.grade_data))
            st.success(f"Added {course_type} '{new_course}'")
    courses_dict = st.session_state.grade_data[grade_level]
    if not courses_dict:
        st.info("No courses added yet. Please add a course above.")
        st.stop()
    course_for_final = st.selectbox("Which course?", list(courses_dict.keys()), key=f"final_{grade_level}")
    entry = courses_dict[course_for_final]
    new_final = st.number_input(
        "Final Exam %",
        min_value=0.0, max_value=100.0,
        value=float(entry.get("Final") or 0.0),
        step=0.1
    )
    if st.button("Unset Final"):
        entry["Final"] = None
        controller.set("grade_data", json.dumps(st.session_state.grade_data))
        st.rerun()
    if st.button("Save Final"):
        entry["Final"] = new_final
        controller.set("grade_data", json.dumps(st.session_state.grade_data))
        st.success("✅ Final saved!")
    total_cred = total_uw = total_w = 0.0
    for vals in courses_dict.values():
        final = vals.get("Final")
        if final is not None:
            creds = vals.get("Credits", 1.0)
            mps = [vals.get(f"MP{i}") for i in range(1, 5) if vals.get(f"MP{i}") is not None]
            avg = sum(mps) / len(mps) if mps else 0.0
            overall = 0.9 * avg + 0.1 * final
            letter = percent_to_letter(overall)
            cp = letter_to_cp[letter]
            bump = 0 if vals.get("Type") == "CP" else (0.5 if vals["Type"] == "Honors" else 1.0)
            total_cred += creds
            total_uw += cp * creds
            total_w += (cp + bump) * creds
    if total_cred:
        uw_gpa = total_uw / total_cred
        w_gpa = total_w / total_cred
        st.subheader(f"GPA — Unweighted: {uw_gpa:.2f} | Weighted: {w_gpa:.2f}")
    else:
        st.subheader("GPA — No finals yet")
    rows = []
    for c, vals in courses_dict.items():
        row = {
            "Course": c,
            "Type": vals.get("Type", "CP"),
            "Credits": f"{vals.get('Credits', 1.0):.1f}"
        }
        mps_list = []
        for i in range(1, 5):
            v = vals.get(f"MP{i}")
            if v is None:
                row[f"MP{i}"] = "NA"
            else:
                row[f"MP{i}"] = f"{v:.1f}% ({percent_to_letter(v)})"
                mps_list.append(v)
        if mps_list:
            avg = sum(mps_list) / len(mps_list)
            row["MP Avg"] = f"{avg:.1f}% ({percent_to_letter(avg)})"
        else:
            row["MP Avg"] = "NA"
        fin = vals.get("Final")
        if fin is None:
            row["Final Exam"] = row["Final Grade"] = "NA"
        else:
            overall = 0.9 * (sum(mps_list) / len(mps_list)) + 0.1 * fin if mps_list else fin
            row["Final Exam"] = f"{fin:.1f}% ({percent_to_letter(fin)})"
            row["Final Grade"] = f"{overall:.1f}% ({percent_to_letter(overall)})"
        row["Goal"] = vals.get("Goal") or "NA"
        reqv = vals.get("Required")
        row["Req Final"] = f"{reqv:.1f}%" if reqv is not None else "NA"
        rows.append(row)
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
    remove_course = st.selectbox("Remove course", df["Course"].tolist())
    if st.button("Remove"):
        courses_dict.pop(remove_course, None)
        controller.set("grade_data", json.dumps(st.session_state.grade_data))
        st.rerun()
