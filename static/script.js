const API_URL = window.location.origin;

// Dynamic login button: makes it so that login is considered 
// "active" when both user and pass are filled
//"inactive" otherwise
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const loginButton = loginForm ? loginForm.querySelector('button[type="submit"]') : null;

    function updateLoginButton() {
        if (loginButton && usernameInput && passwordInput) {
            const usernameFilled = usernameInput.value.trim() !== '';
            const passwordFilled = passwordInput.value.trim() !== '';
            
            if (usernameFilled && passwordFilled) {
                loginButton.classList.add('active');
                loginButton.disabled = false;
            } else {
                loginButton.classList.remove('active');
                loginButton.disabled = true;
            }
        }
    }

    //event listeners to inputs
    if (usernameInput && passwordInput) {
        usernameInput.addEventListener('input', updateLoginButton);
        passwordInput.addEventListener('input', updateLoginButton);
        
        //Checks if  page loads already filled (it shouldnt)
        updateLoginButton();
    }
});

// Login form handler
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorMessage = document.getElementById('errorMessage');

            try {
                const response = await fetch(`${API_URL}/api/login`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include',
                    body: JSON.stringify({ username, password })
                });

                const data = await response.json();

                if (data.success) {
                    // Store user info in localStorage
                    localStorage.setItem('user', JSON.stringify(data.user));
                    // Redirect to appropriate page
                    window.location.href = data.redirect;
                } else {
                    errorMessage.textContent = data.message;
                }
            } catch (error) {
                errorMessage.textContent = 'Login failed. Please try again.';
                console.error('Error:', error);
            }
        });
    }
});

// Logout function (can be used on other pages)
async function logout() {
    try {
        await fetch(`${API_URL}/api/logout`, {
            method: 'POST',
        });
        localStorage.removeItem('user');
        //potential redirect
        window.location.href = '/';
    } catch (error) {
        console.error('Logout error:', error);
        //Incase, redirects to home
        window.location.href = '/';
    }
}

// Sign out handler for all pages
document.addEventListener('DOMContentLoaded', () => {
    const signOutBtn = document.getElementById('signOutBtn');

    if (signOutBtn) {
        signOutBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            await logout();
        });
    }

    // Load username on all pages that have username, not just coursepage html
    const usernameSpan = document.getElementById('username');
    if (usernameSpan) {
        const user = JSON.parse(localStorage.getItem('user'));
        if (user) {
            usernameSpan.textContent = user.username;
        }
    }
});

async function loadTeacherCourses(container) {
    try {
        const res = await fetch(`${API_URL}/api/teacher/courses`, { credentials: 'include' });
        if (!res.ok) {
            if (res.status === 401) {
                window.location.href = '/';
                return;
            }
            throw new Error('Failed to load courses');
        }
        const data = await res.json();
        renderTeacherCourses(container, data.courses || []);
    } catch (err) {
        console.error(err);
        container.innerHTML = '<div class="empty">Failed to load courses.</div>';
    }
}

function renderTeacherCourses(container, courses) {
    if (!courses.length) {
        container.innerHTML = '<div class="empty">No courses assigned.</div>';
        return;
    }

    container.innerHTML = courses.map(c => {
        const rows = (c.students || []).map(s => {
            const grade = (s.grade === null || s.grade === undefined) ? 'N/A' : s.grade;
            const gradeCellId = `grade-${s.id}`;
            return `
                <tr>
                    <td>${escapeHtml(s.student_name || 'Unknown')}</td>
                    <td id="${gradeCellId}">${grade}</td>
                    <td><button onclick="editGrade(${s.id})">Edit</button></td>
                </tr>
            `;
        }).join('');

        const studentsTable = rows
            ? `
                <table>
                    <thead>
                        <tr>
                            <th>Student</th>
                            <th>Grade</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
              `
            : `<div class="empty">No students enrolled.</div>`;

        return `
            <div class="course-card">
                <div class="course-head">
                    <div><strong>${escapeHtml(c.course_name)}</strong> (${escapeHtml(c.course_code)})</div>
                    <div class="course-meta">${escapeHtml(c.time)} • Enrolled: ${c.enrolled_count || (c.students ? c.students.length : 0)}/${c.capacity}</div>
                </div>
                <div class="course-body">
                    ${studentsTable}
                </div>
            </div>
        `;
    }).join('');
}

window.editGrade = async function editGrade(enrollmentId) {
    const cellId = `grade-${enrollmentId}`;
    const td = document.getElementById(cellId);
    if (!td) return;

    const current = td.textContent === 'N/A' ? '' : td.textContent.trim();
    const input = prompt('Enter new grade (0-100):', current);
    if (input === null) return;

    const grade = parseInt(input, 10);
    if (Number.isNaN(grade) || grade < 0 || grade > 100) {
        alert('Please enter a valid number between 0 and 100.');
        return;
    }

    try {
        const res = await fetch(`${API_URL}/api/grade`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ enrollment_id: enrollmentId, grade })
        });

        const data = await res.json();
        if (!res.ok || !data.success) {
            alert(data.message || 'Failed to update grade.');
            return;
        }

        td.textContent = String(grade);
        alert('Grade updated successfully.');
    } catch (err) {
        console.error(err);
        alert('Failed to update grade.');
    }
};

// DOM hook for teacher dashboard
document.addEventListener('DOMContentLoaded', () => {
    const teacherContainer = document.getElementById('teacherCourses');
    if (teacherContainer) {
        loadTeacherCourses(teacherContainer);
    }
});

// HTML escaper
function escapeHtml(str) {
    return String(str)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

/* ===== Student Dashboard ===== */

async function fetchStudentCourses() {
    const res = await fetch(`${API_URL}/api/student/courses`, { credentials: 'include' });
    if (res.status === 401) {
        window.location.href = '/';
        return [];
    }
    if (!res.ok) throw new Error('Failed to load student courses');
    const data = await res.json();
    return data.courses || [];
}

async function fetchAllCourses() {
    const res = await fetch(`${API_URL}/api/courses`, { credentials: 'include' });
    if (!res.ok) throw new Error('Failed to load all courses');
    const data = await res.json();
    return data.courses || [];
}

function renderMyCourses(container, my) {
    if (!my.length) {
        container.innerHTML = `<div class="empty">You are not enrolled in any courses.</div>`;
        return;
    }

    const rows = my.map(item => {
        const c = item.course;
        const grade = (item.grade === null || item.grade === undefined) ? 'N/A' : item.grade;
        return `
      <tr>
        <td>${escapeHtml(c.course_name)} (${escapeHtml(c.course_code)})</td>
        <td>${escapeHtml(c.teacher_name || 'TBA')}</td>
        <td>${escapeHtml(c.time)}</td>
        <td>${c.enrolled_count}/${c.capacity}</td>
        <td>${grade}</td>
        <td><button onclick="dropCourse(${c.id})">Drop</button></td>
      </tr>
    `;
    }).join('');

    container.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Course</th>
          <th>Instructor</th>
          <th>Time</th>
          <th>Enrolled</th>
          <th>Grade</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderAllCourses(container, allCourses, enrolledIds) {
    if (!allCourses.length) {
        container.innerHTML = `<div class="empty">No courses available.</div>`;
        return;
    }

    const rows = allCourses.map(c => {
        const isEnrolled = enrolledIds.has(c.id);
        const isFull = !!c.is_full;
        const disabled = isEnrolled || isFull;
        const status = isEnrolled ? 'Enrolled' : (isFull ? 'Full' : 'Open');
        const buttonClass = isFull ? 'full' : '';

        return `
      <tr>
        <td>${escapeHtml(c.course_name)} (${escapeHtml(c.course_code)})</td>
        <td>${escapeHtml(c.teacher_name || 'TBA')}</td>
        <td>${escapeHtml(c.time)}</td>
        <td>${c.enrolled_count}/${c.capacity}</td>
        <td>${status}</td>
        <td>
          <button class="${buttonClass}" ${disabled ? 'disabled' : ''} onclick="enrollInCourse(${c.id})">Enroll</button>
        </td>
      </tr>
    `;
    }).join('');

    container.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Course</th>
          <th>Instructor</th>
          <th>Time</th>
          <th>Enrolled</th>
          <th>Status</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}


async function loadStudentDashboard() {
    const myContainer = document.getElementById('myCourses');
    const allContainer = document.getElementById('allCourses');
    if (!myContainer && !allContainer) return;

    try {
        const my = await fetchStudentCourses();
        renderMyCourses(myContainer, my);

        const enrolledSet = new Set(my.map(x => x.course.id));
        const all = await fetchAllCourses();
        renderAllCourses(allContainer, all, enrolledSet);
    } catch (e) {
        console.error(e);
        if (myContainer) myContainer.innerHTML = `<div class="empty">Failed to load your courses.</div>`;
        if (allContainer) allContainer.innerHTML = `<div class="empty">Failed to load all courses.</div>`;
    }
}

window.enrollInCourse = async function enrollInCourse(courseId) {
    try {
        const res = await fetch(`${API_URL}/api/enroll`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ course_id: courseId })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            alert(data.message || 'Failed to enroll.');
            return;
        }
        await loadStudentDashboard();
        alert('Enrolled successfully.');
    } catch (e) {
        console.error(e);
        alert('Failed to enroll.');
    }
};

window.dropCourse = async function dropCourse(courseId) {
    if (!confirm('Drop this course?')) return;
    try {
        const res = await fetch(`${API_URL}/api/drop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ course_id: courseId })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            alert(data.message || 'Failed to drop.');
            return;
        }
        await loadStudentDashboard();
        alert('Dropped successfully.');
    } catch (e) {
        console.error(e);
        alert('Failed to drop.');
    }
};

/* Tab switching + initialization */
document.addEventListener('DOMContentLoaded', () => {
    const tabMy = document.getElementById('tabMy');
    const tabAdd = document.getElementById('tabAdd');
    const mySection = document.getElementById('mySection');
    const addSection = document.getElementById('addSection');

    if (tabMy && tabAdd && mySection && addSection) {
        const activate = (which) => {
            if (which === 'my') {
                tabMy.classList.add('active'); tabAdd.classList.remove('active');
                mySection.style.display = ''; addSection.style.display = 'none';
            } else {
                tabAdd.classList.add('active'); tabMy.classList.remove('active');
                addSection.style.display = ''; mySection.style.display = 'none';
            }
        };

        tabMy.addEventListener('click', () => activate('my'));
        tabAdd.addEventListener('click', () => activate('add'));
    }

    if (document.getElementById('myCourses') || document.getElementById('allCourses')) {
        loadStudentDashboard();
    }
});
