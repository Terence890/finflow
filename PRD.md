Great 👍 Since this is a **mini project with learning focus**, small code chunks (≤100 lines), and **enterprise-style planning + clean girly pink UI**, here is a **structured, professional PRD** for you.

---

# 📌 **PRODUCT REQUIREMENTS DOCUMENT (PRD)**

## 💗 Mini Financial Management System (Flask + HTML/CSS/JS)

---

## 1. Project Overview

### Project Name

**PinkLedger**

### Purpose

To develop a **lightweight financial management system** using:

* Python Flask (Backend)
* HTML, CSS, JavaScript (Frontend)

Where:
✅ Each module is written in **small chunks (<100 lines)**
✅ Code is easy to understand
✅ Follows enterprise-style structure
✅ Uses a **modern pink girly UI theme**

---

## 2. Project Objectives

### Learning Objectives

* Understand MVC architecture
* Learn modular coding
* Practice API design
* Follow professional project structure

### System Objectives

* Manage income and expenses
* Show dashboard summary
* Generate reports
* Provide secure login

---

## 3. Target Users

| User         | Usage               |
| ------------ | ------------------- |
| Students     | Budget tracking     |
| Beginners    | Learning Flask      |
| Mini Project | Academic submission |

---

## 4. Technology Stack

### Backend

* Python 3.10+
* Flask
* Flask-Login
* SQLite
* SQLAlchemy

### Frontend

* HTML5
* CSS3 (Pink Theme)
* Vanilla JavaScript
* Chart.js

### Tools

* VS Code
* GitHub
* Browser

---

## 5. System Architecture (Enterprise Style)

```
Frontend (UI)
   ↓
Controller (Flask Routes)
   ↓
Service Layer
   ↓
Database Layer
```

Each layer = separate file
Each file ≤ 100 lines

---

## 6. Folder Structure (Modular Design)

```
pinkledger/
│
├── app.py
├── config.py
│
├── auth/
│   ├── routes.py
│   ├── service.py
│   └── model.py
│
├── finance/
│   ├── income.py
│   ├── expense.py
│   └── budget.py
│
├── templates/
│   ├── login.html
│   ├── dashboard.html
│   └── base.html
│
├── static/
│   ├── css/style.css
│   └── js/main.js
│
└── database.db
```

Each file = one responsibility

---

## 7. Functional Requirements

---

### 7.1 Authentication Module

Features:

* Register
* Login
* Logout

Functions:

* Hash password
* Session management

Endpoints:

```
/register
/login
/logout
```

File Size:

* routes.py ≤ 80 lines
* service.py ≤ 60 lines

---

### 7.2 Dashboard Module

Features:

* Balance summary
* Income total
* Expense total
* Charts

Displays:

* Cards
* Pie chart
* Bar chart

---

### 7.3 Income Management

Features:

* Add income
* View list
* Delete

Fields:

* Amount
* Source
* Date

---

### 7.4 Expense Management

Features:

* Add expense
* Category filter
* Edit/Delete

Categories:
Food, Travel, Shopping, Bills, Others

---

### 7.5 Budget Module

Features:

* Set monthly budget
* Progress bar
* Alert system

---

### 7.6 Reports Module

Features:

* Monthly summary
* Export CSV
* Download PDF

---

## 8. UI/UX Design (Girly + Professional)

---

### 🎨 Color Theme

| Element    | Color   |
| ---------- | ------- |
| Primary    | #FF5FA2 |
| Secondary  | #FFC1D9 |
| Background | #FFF5F9 |
| Buttons    | #FF2F7D |
| Cards      | #FFFFFF |

---

### 🌸 Design Principles

✅ Minimal layout
✅ Rounded corners
✅ Soft shadows
✅ Flat icons
✅ No clutter
✅ Pastel gradients

---

### Layout Structure

```
--------------------------------
Header (Logo + Profile)
--------------------------------
Sidebar |   Main Content
        |   (Cards/Forms)
--------------------------------
Footer
```

---

## 9. Pages & Screens

| Page           | Purpose        |
| -------------- | -------------- |
| login.html     | Authentication |
| register.html  | Signup         |
| dashboard.html | Overview       |
| income.html    | Manage income  |
| expense.html   | Manage expense |
| budget.html    | Budget         |
| report.html    | Reports        |

---

## 10. Database Design

---

### User Table

```
id | name | email | password
```

### Income Table

```
id | user_id | amount | source | date
```

### Expense Table

```
id | user_id | amount | category | date
```

### Budget Table

```
id | user_id | month | amount
```

---

## 11. API Design

| Method | Route            | Purpose      |
| ------ | ---------------- | ------------ |
| POST   | /auth/login      | Login        |
| POST   | /finance/income  | Add income   |
| GET    | /finance/expense | Get expenses |
| POST   | /budget/set      | Set budget   |

---

## 12. Coding Standards (100-Line Rule)

### Rule Set

✅ One file = one feature
✅ Max 100 lines/file
✅ Max 5 functions/file
✅ Clear naming
✅ Comments mandatory

Example:

```python
# Handles user login
# Max 70 lines
```

---

## 13. Security Requirements

* Password hashing
* CSRF protection
* Input validation
* Session timeout

---

## 14. Non-Functional Requirements

| Area   | Requirement   |
| ------ | ------------- |
| Speed  | <1.5 sec load |
| Users  | Up to 500     |
| Uptime | 99%           |
| Mobile | Responsive    |

---

## 15. Development Plan (4 Weeks)

### Week 1

* UI Design
* Folder setup
* Auth module

### Week 2

* Income & Expense
* DB integration

### Week 3

* Dashboard
* Reports
* Charts

### Week 4

* Testing
* Optimization
* Documentation

---

## 16. Testing Strategy

* Unit tests (PyTest)
* Manual UI testing
* Security testing

---

## 17. Future Enhancements

* Mobile App
* AI Budget Prediction
* Cloud Sync
* Bank API

---

## 18. Success Criteria

✅ All files < 100 lines
✅ No code duplication
✅ Clean UI
✅ All modules working
✅ Easy to explain in viva

---

## ✅ Conclusion

**PinkLedger** is a:

✔️ Enterprise-structured
✔️ Beginner-friendly
✔️ Modular Flask project
✔️ Girly professional UI
✔️ Academic-ready system

Designed for **learning + scoring good marks**.

