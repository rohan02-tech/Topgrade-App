/*
  app.js
  Frontend logic for the TOP GRADE app.

  Flow (as decided):
    1. Home page - shows both courses (Python + Java) to everyone, logged in or not.
    2. Login page - simple name-based login for the 2 demo students (Rohan, Aman).
    3. Once Rohan logs in, the app knows he's enrolled in Python. His course card
       shows "Enrolled - Continue" and opens straight into the lesson list.
       Aman, once logged in, sees both courses but neither is enrolled, so he
       gets an "Enroll" button instead.

  Talks to the Flask backend:
    GET  /api/courses
    GET  /api/my-courses/<student_id>
    POST /api/enroll     { student_id, course_id }
    POST /api/unenroll   { student_id, course_id }
*/

// API_BASE now comes from config.js (loaded before this file in index.html)

// Very small demo "auth": map typed names to seeded student ids.
const DEMO_STUDENTS = {
  "rohan": { id: 1, name: "Rohan" },
  "aman": { id: 2, name: "Aman" },
};

let currentUser = null;       // { id, name } once logged in
let currentView = "home";     // home | login | course | mylearning | notifications | profile
let allCourses = [];          // cache of GET /api/courses
let myEnrolledCourseIds = new Set(); // populated after login

const app = document.getElementById("app");
const headerAction = document.getElementById("headerAction");

function money(n) {
  return "Rs. " + n.toLocaleString("en-IN");
}

async function fetchCourses() {
  const res = await fetch(`${API_BASE}/api/courses`);
  allCourses = await res.json();
}

async function fetchMyCourses(studentId) {
  const res = await fetch(`${API_BASE}/api/my-courses/${studentId}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.enrolled_courses.map(c => c.id);
}

async function enroll(courseId) {
  if (!currentUser) { renderLogin(); return; }
  await fetch(`${API_BASE}/api/enroll`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student_id: currentUser.id, course_id: courseId }),
  });
  myEnrolledCourseIds.add(courseId);
  await fetchCourses(); // refresh students_enrolled counts
  renderHome();
}

function setHeaderAction() {
  if (currentUser) {
    headerAction.textContent = `Hi, ${currentUser.name}`;
    headerAction.onclick = () => renderProfile();
  } else {
    headerAction.textContent = "Login";
    headerAction.onclick = () => renderLogin();
  }
}

function setActiveNav(view) {
  document.querySelectorAll("nav div").forEach(el => {
    el.classList.toggle("active", el.dataset.view === view);
  });
}

function courseCard(course) {
  const isEnrolled = myEnrolledCourseIds.has(course.id);
  const lessonsHtml = course.lessons.map(l =>
    `<li>${l.title} <span style="color:#999">(${l.duration})</span></li>`
  ).join("");

  let actionHtml;
  if (currentUser && isEnrolled) {
    actionHtml = `<button class="btn" onclick="renderCourse(${course.id})">Continue Learning</button>`;
  } else if (currentUser && !isEnrolled) {
    actionHtml = `<button class="btn" onclick="enroll(${course.id})">Enroll Now - ${money(course.price)}</button>`;
  } else {
    actionHtml = `<button class="btn secondary" onclick="renderLogin()">Login to Enroll</button>`;
  }

  return `
    <div class="course-card">
      <h2>${course.title} ${isEnrolled ? '<span class="badge">Enrolled</span>' : ""}</h2>
      <p class="meta">${course.category} &middot; ${course.duration} &middot; ${course.students_enrolled} students</p>
      <p class="desc">${course.description}</p>
      <ul class="lesson-list">${lessonsHtml}</ul>
      ${actionHtml}
    </div>
  `;
}

async function renderHome() {
  currentView = "home";
  setActiveNav("home");
  setHeaderAction();
  app.innerHTML = "<p>Loading courses...</p>";
  if (allCourses.length === 0) await fetchCourses();
  app.innerHTML = allCourses.map(courseCard).join("");
}

function renderLogin() {
  currentView = "login";
  setActiveNav("");
  app.innerHTML = `
    <div class="login-box">
      <h2>Login to TOP GRADE</h2>
      <input type="text" id="loginName" placeholder="Enter your name (Rohan or Aman)" />
      <button class="btn" onclick="doLogin()">Login</button>
      <div id="loginError"></div>
      <p class="login-hint">Demo accounts: Rohan (enrolled in Python), Aman (not enrolled yet)</p>
    </div>
  `;
}

async function doLogin() {
  const typed = document.getElementById("loginName").value.trim().toLowerCase();
  const match = DEMO_STUDENTS[typed];
  const errorBox = document.getElementById("loginError");

  if (!match) {
    errorBox.innerHTML = `<p class="error-text">Student not found. Try "Rohan" or "Aman".</p>`;
    return;
  }

  currentUser = match;
  const enrolledIds = await fetchMyCourses(currentUser.id);
  myEnrolledCourseIds = new Set(enrolledIds);

  // Per requirement: once Rohan logs in, take him straight into his enrolled course.
  if (myEnrolledCourseIds.size > 0) {
    const firstEnrolledId = [...myEnrolledCourseIds][0];
    await fetchCourses();
    renderCourse(firstEnrolledId);
  } else {
    renderHome();
  }
}

function renderCourse(courseId) {
  currentView = "course";
  setActiveNav("mylearning");
  setHeaderAction();
  const course = allCourses.find(c => c.id === courseId);
  if (!course) { renderHome(); return; }

  const isEnrolled = myEnrolledCourseIds.has(course.id);
  const lessonsHtml = course.lessons.map(l => `
    <div class="course-card" style="margin-bottom:8px;">
      <p style="margin:0 0 4px; font-weight:bold;">${l.title}</p>
      <p class="meta" style="margin:0;">Duration: ${l.duration}</p>
      <video controls style="width:100%; margin-top:8px; border-radius:8px; background:#000;">
        <source src="${API_BASE}/${l.video_path}" type="video/mp4">
        Your browser does not support the video tag.
      </video>
    </div>
  `).join("");

  app.innerHTML = `
    <div class="course-card">
      <h2>${course.title} ${isEnrolled ? '<span class="badge">Enrolled</span>' : ""}</h2>
      <p class="meta">${course.category} &middot; ${course.duration}</p>
      <p class="desc">${course.description}</p>
    </div>
    <h3 style="margin: 16px 0 8px;">Lessons</h3>
    ${lessonsHtml}
    <button class="btn secondary" onclick="renderHome()">Back to Home</button>
  `;
}

function renderMyLearning() {
  currentView = "mylearning";
  setActiveNav("mylearning");
  setHeaderAction();

  if (!currentUser) {
    app.innerHTML = `<p style="text-align:center; margin-top:40px; color:#777;">Please log in to see your enrolled courses.</p>
      <button class="btn" style="display:block; margin: 0 auto;" onclick="renderLogin()">Login</button>`;
    return;
  }

  const enrolled = allCourses.filter(c => myEnrolledCourseIds.has(c.id));
  if (enrolled.length === 0) {
    app.innerHTML = `<p style="text-align:center; margin-top:40px; color:#777;">You are not enrolled in any course yet.</p>
      <button class="btn" style="display:block; margin: 0 auto;" onclick="renderHome()">Browse Courses</button>`;
    return;
  }

  app.innerHTML = enrolled.map(courseCard).join("");
}

function renderNotifications() {
  currentView = "notifications";
  setActiveNav("notifications");
  setHeaderAction();
  app.innerHTML = `<p style="text-align:center; margin-top:40px; color:#777;">No new notifications.</p>`;
}

function renderProfile() {
  currentView = "profile";
  setActiveNav("profile");
  setHeaderAction();

  if (!currentUser) {
    renderLogin();
    return;
  }

  app.innerHTML = `
    <div class="login-box">
      <h2>${currentUser.name}</h2>
      <p style="color:#777; font-size:13px;">Logged in to TOP GRADE</p>
      <button class="btn secondary" onclick="logout()">Log Out</button>
    </div>
  `;
}

function logout() {
  currentUser = null;
  myEnrolledCourseIds = new Set();
  renderHome();
}

// Nav wiring
document.querySelectorAll("nav div").forEach(el => {
  el.addEventListener("click", () => {
    const view = el.dataset.view;
    if (view === "home") renderHome();
    else if (view === "mylearning") renderMyLearning();
    else if (view === "notifications") renderNotifications();
    else if (view === "profile") renderProfile();
  });
});

// Initial load
renderHome();
