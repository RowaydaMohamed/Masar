"""
Bylaw data (Helwan - Faculty of Computers & AI, new bylaw) transcribed from the PDF.
Pure Python: no Django imports, so validate() can run anywhere (CI, shell).

!! The PDF text is reversed Arabic. Course codes are reliable; PREREQ_TEXT must be
!! checked by a second person against the original PDF before the demo.
"""

# ---- Departments ---------------------------------------------------------------------
DEPARTMENTS = {
    "CS": ("Computer Science", "علوم الحاسب"),
    "IT": ("Information Technology", "تكنولوجيا المعلومات"),
    "IS": ("Information Systems", "نظم المعلومات"),
    "AI": ("Artificial Intelligence", "الذكاء الاصطناعي"),
}

# ---- General (Art. 19): 6 compulsory + 6 elective -------------------------------------
GENERAL_COMPULSORY = {
    "HU111": ("English I", 2),
    "HU112": ("English II", 2),
    "HU313": ("Human Rights and Anti-Corruption", 2),
}
GENERAL_ELECTIVE = {
    "HU121": ("Fundamentals of Economics", 3),
    "HU213": ("English III", 3),
    "HU323": ("Fundamentals of Accounting", 3),
    "HU331": ("Communication and Negotiation Skills", 3),
    "HU332": ("Creative Thinking", 3),
    "HU333": ("Mass Communication", 3),
    "HU334": ("Professional Ethics", 3),
}

# ---- Faculty (Art. 20): 63 compulsory + 9 elective ------------------------------------
FACULTY_COMPULSORY = {
    "MA111": ("Mathematics 1", 3), "MA112": ("Discrete Mathematics", 3),
    "MA113": ("Mathematics 2", 3), "ST121": ("Probability and Statistics 1", 3),
    "IT111": ("Electronics 1", 3), "PH111": ("Physics", 3),
    "CS111": ("Introduction to Computers", 3), "CS112": ("Programming 1", 3),
    "CS221": ("Logic Design", 3), "CS214": ("Data Structures", 3),
    "CS316": ("Algorithms", 3), "IT221": ("Data Communication", 3),
    "IS240": ("Operations Research", 3), "IS231": ("Fundamentals of Information Systems", 3),
    "IS211": ("Database System 1", 3), "IS351": ("System Analysis and Design 1", 3),
    "IT222": ("Computer Networks 1", 3), "IT223": ("Internet Technology", 3),
    "CS241": ("Operating Systems 1", 3), "CS251": ("Software Engineering 1", 3),
    "CS213": ("Programming 2", 3),
}
FACULTY_ELECTIVE = {
    "ST122": ("Statistics and Probability 2", 3), "HU122": ("Fundamentals of Management", 3),
    "IS321": ("Management Projects", 3), "IT241": ("Signals and Systems", 3),
    "IS241": ("Modeling and Simulation", 3), "IS342": ("Simulation Languages", 3),
    "IT211": ("Computer Maintenance", 3), "CS313": ("Programming 3", 3),
}

# ---- Department-group courses (names; credits default 3, projects 6) -------------------
DEPT_COURSE_NAMES = {
    "AI330": "Machine Learning", "CS322": "Computer Organization", "IT331": "Computer Graphics 1",
    "CS352": "Software Engineering 2", "CS471": "Parallel Processing and High Performance Computing",
    "AI310": "Artificial Intelligence", "CS419": "Compilers", "CS405": "Theory of Computation",
    "CS342": "Operating Systems 2", "CS460": "Distributed Systems and Cloud Computing",
    "IT423": "Information and Computer Networks Security", "CS498": "Project",
    "AI335": "Neural Networks and Deep Learning", "AI360": "Natural Language Processing",
    "IT441": "Image Processing 1", "AI350": "Data Visualization", "AI380": "Human Computer Interaction",
    "CS410": "Concepts of Programming Languages", "CS480": "Cryptography", "CS416": "Advanced Algorithms",
    "IT312": "Microprocessors", "IT414": "Embedded Systems", "IS312": "Database Systems 2",
    "IT444": "Computer Vision", "IT433": "Multimedia", "IT342": "Pattern Recognition",
    "CS496": "Selected Topics in Computer Science",
    "IT311": "Computer Architecture", "IT321": "Communication Technology", "IT322": "Computer Networks 2",
    "IT341": "Digital Signal Processing", "IT498": "Project",
    "IT411": "Distributed and Parallel Computer Systems", "IT412": "Real Time Systems",
    "IS345": "Internet Applications", "IT431": "Virtual Reality", "IT332": "Computer Graphics 2",
    "IT443": "Speech Processing", "IT313": "Computer Interfaces", "IT422": "Wireless and Mobile Networks",
    "IT442": "Image Processing 2", "IT415": "Robotics", "IT455": "Image, Audio and Video Processing",
    "IT456": "3D Modeling and Animation", "IT457": "Game Development",
    "IT425": "Embedded Internet of Things Systems", "IT496": "Selected Topics in Information Technology",
    "IS313": "Data Storage and Retrieval", "IS352": "Analysis and Design of Information Systems 2",
    "IS414": "Information Systems Security", "IS451": "Decision Support Systems",
    "IS333": "Management Information Systems", "IS350": "Business Intelligence and Data Analytics",
    "IS365": "Big Data Technologies", "IS360": "Introduction to Data Science",
    "IS448": "Knowledge Base Management", "IS498": "Project",
    "IS421": "Data Mining", "IS415": "Object Oriented Databases",
    "IS453": "Information Systems Development Methodologies", "IS441": "Intelligent Information Systems",
    "IS442": "E-Commerce", "IS434": "Quality Assurance of Information Systems and Programming",
    "IS435": "Information Centers Management", "IS334": "Accounting Information Systems",
    "IS422": "Data Warehousing", "IS416": "Distributed Databases",
    "IS443": "Geographical Information Systems", "IS444": "Multimedia Information Systems",
    "IS450": "Software Testing and Integration", "IS455": "Software Quality Assurance and Testing",
    "IS460": "Introduction to Deep Learning", "IS496": "Selected Topics in Information Systems",
    "AI320": "Convex Optimization Theory", "AI420": "Evolutionary Algorithms",
    "AI430": "Computational Intelligence", "AI370": "Advanced Machine Learning",
    "AI460": "Natural Language Understanding", "AI498": "Project", "AI490": "Bioinformatics",
    "AI457": "Knowledge Representation", "AI435": "Spoken Language Processing",
    "AI496": "Selected Topics in Artificial Intelligence",
}
PROJECT_CODES = {"CS498", "IT498", "IS498", "AI498"}      # 6 credits each

DEPT_COMPULSORY = {
    "CS": "AI330 CS322 IT331 CS352 CS471 AI310 CS419 CS405 CS342 CS460 IT423 CS498".split(),
    "IT": "IT311 IT321 IT322 IT331 IT341 IT342 IT433 IT441 AI310 IT444 IT423 IT498".split(),
    "IS": "IS345 IS312 IS313 IS352 IS414 IS451 IS333 IS350 IS365 IS360 IS448 IS498".split(),
    "AI": "AI310 IT441 AI320 AI420 AI330 AI430 AI335 AI360 AI370 IS365 AI460 AI498".split(),
}
DEPT_ELECTIVE = {
    "CS": ("AI335 AI360 IT441 AI350 AI380 CS410 CS480 CS416 IT312 IT414 "
           "IS312 IT444 IT433 IT342 CS496").split(),
    "IT": ("IT411 IT412 IS345 IT431 IT332 IT443 IS312 CS352 IT312 IT313 IT422 IT442 IT414 "
           "IT415 IT455 IT456 IT457 IT425 IT496").split(),
    "IS": ("IS421 IS415 IS453 AI310 IS441 IS442 IS434 CS352 IS435 IS334 IS422 IS416 IS443 "
           "IS444 IT423 IS450 IS455 IS460 IS496").split(),
    "AI": ("IT312 CS480 CS471 CS460 IT414 CS416 IT341 AI380 AI490 IT443 IT444 IS360 AI457 "
           "IS312 IT415 AI435 AI350 IT425 AI496").split(),
}

# ---- Prerequisites: "course<pre1+pre2" => ONE group, all required (AND) ---------------
PREREQ_TEXT = """
HU213<HU111+HU112 MA113<MA111 CS112<CS111 CS221<CS111 CS214<CS112 CS316<CS214
IT221<ST121 IS351<IS231 IT222<IT221 CS241<CS112 CS251<CS112 CS213<CS112
ST122<ST121 IS321<IS240 IT241<MA113 IS342<IS241 CS313<CS213
AI330<ST122 CS322<CS221 IT331<CS112 CS352<CS251 CS471<CS241 AI310<CS316
CS419<CS214 CS405<MA112 CS342<CS241 CS460<IT222 IT423<IT222 CS498<CS251
IT311<CS221 IT321<IT221 IT322<IT222 IT341<MA112 IT433<CS112 IT441<IT241 IT444<CS316 IT498<IT222
IS345<IT223 IS312<IS211 IS313<IS211 IS352<IS351 IS414<IS211 IS451<IS231
IS333<IS231 IS350<ST122 IS365<IS211 IS360<IS312 IS448<IS312 IS498<IS351
AI320<MA113 AI420<AI320 AI430<AI310 AI335<AI330 AI360<AI310 AI370<AI330
AI460<AI360 AI498<CS251
AI350<ST122 AI380<AI310 AI490<AI310 AI457<AI310 AI435<AI360 CS410<CS112
CS480<ST121 CS416<CS316 IT312<CS221 IT414<IT312 IT411<IT311 IT412<IT311
IT313<IT311 IT431<IT331 IT332<IT331 IT443<IT241 IT422<IT322 IT442<IT441
IT415<MA112 IT455<IT443 IT456<IT331 IT457<IT331 IT425<IT414
IS421<IS211 IS415<IS211 IS453<IS352 IS441<AI310 IS442<IS345 IS434<IS352
IS334<IS231 IS422<IS211 IS416<IS211 IS443<IS211 IS444<IS211 IS450<IS352
IS455<IS231 IS460<IS448
"""

# ---- AI model: 24 features in the exact training order -> course codes -----------------
AI_FEATURE_COURSES = [
    "CS316", "IT222", "IT221", "CS214", "IS211", "MA112", "IT111", "HU111", "HU112",
    "IS231", "HU313", "IT223", "CS111", "CS221", "MA111", "MA113", "CS241", "IS240",
    "PH111", "ST121", "CS112", "CS213", "CS251", "IS351",
]


# ---- helpers ------------------------------------------------------------------------
def parse_prereqs(text=PREREQ_TEXT):
    """-> {course_code: [ [codes in group 1], ... ]} (single group per course in this bylaw)."""
    out = {}
    for token in text.split():
        course, pres = token.split("<")
        out[course] = [pres.split("+")]
    return out


def all_courses():
    """-> {code: dict(name, credits, group, type)}; type is None for department courses."""
    c = {}
    for code, (n, h) in GENERAL_COMPULSORY.items():
        c[code] = dict(name=n, credits=h, group="general", type="compulsory")
    for code, (n, h) in GENERAL_ELECTIVE.items():
        c[code] = dict(name=n, credits=h, group="general", type="elective")
    for code, (n, h) in FACULTY_COMPULSORY.items():
        c[code] = dict(name=n, credits=h, group="faculty", type="compulsory")
    for code, (n, h) in FACULTY_ELECTIVE.items():
        c[code] = dict(name=n, credits=h, group="faculty", type="elective")
    for code, n in DEPT_COURSE_NAMES.items():
        c[code] = dict(name=(f"{n} ({code[:2]})" if code in PROJECT_CODES else n),
                       credits=6 if code in PROJECT_CODES else 3, group="department", type=None)
    for code, d in c.items():
        d["min_level"] = int(code[2])          # first digit of the numeric part
    return c


def validate():
    """Raises AssertionError on any inconsistency. Returns a summary dict."""
    c = all_courses()
    assert sum(d["credits"] for d in c.values() if d["group"] == "general" and d["type"] == "compulsory") == 6
    assert sum(d["credits"] for d in c.values() if d["group"] == "faculty" and d["type"] == "compulsory") == 63
    assert len(FACULTY_COMPULSORY) == 21 and len(FACULTY_ELECTIVE) == 8 and len(GENERAL_ELECTIVE) == 7
    for dept in DEPARTMENTS:
        for code in DEPT_COMPULSORY[dept] + DEPT_ELECTIVE[dept]:
            assert code in DEPT_COURSE_NAMES, f"{dept}: unknown department course {code}"
        assert len(set(DEPT_COMPULSORY[dept])) == len(DEPT_COMPULSORY[dept]), dept
        assert not set(DEPT_COMPULSORY[dept]) & set(DEPT_ELECTIVE[dept]), f"{dept}: code in both lists"
        comp = sum(c[x]["credits"] for x in DEPT_COMPULSORY[dept])
        assert comp == 39, f"{dept} compulsory = {comp}, expected 39"
        pool = sum(c[x]["credits"] for x in DEPT_ELECTIVE[dept])
        assert pool >= 21, f"{dept} elective pool = {pool} < 21"
    pre = parse_prereqs()
    for course, groups in pre.items():
        assert course in c, f"prereq for unknown course {course}"
        for g in groups:
            for p in g:
                assert p in c, f"{course}: unknown prerequisite {p}"
                assert p != course
    # cycle check (DFS)
    state = {}
    def dfs(x):
        state[x] = 1
        for g in pre.get(x, []):
            for p in g:
                assert state.get(p) != 1, f"prerequisite cycle through {x} -> {p}"
                if state.get(p) is None:
                    dfs(p)
        state[x] = 2
    for x in pre:
        if state.get(x) is None:
            dfs(x)
    assert len(AI_FEATURE_COURSES) == 24 and len(set(AI_FEATURE_COURSES)) == 24
    for x in AI_FEATURE_COURSES:
        assert x in c and c[x]["group"] in ("general", "faculty") and c[x]["type"] == "compulsory", x
    return {"courses": len(c), "prerequisite_rows": sum(len(g) for v in pre.values() for g in v)}


if __name__ == "__main__":
    print(validate())
