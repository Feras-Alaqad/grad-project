# AWN Platform API

A comprehensive platform that connects organizations with beneficiaries by providing a centralized hub for announcements, aid opportunities, job postings, and institutional programs. AWN enables organizations to publish opportunities while allowing users to easily discover, apply for, and track relevant announcements.

---

## Problem

Many organizations publish aid programs, employment opportunities, and community announcements through scattered channels such as social media pages, messaging groups, and websites. This makes it difficult for beneficiaries to discover opportunities relevant to them.

AWN solves this problem by providing a unified, searchable platform where organizations can publish announcements and beneficiaries can easily access and apply for them.

---

## Features

### Authentication

* JWT-based authentication
* User registration and login
* Password reset and change password functionality
* Secure logout
* User profile management

### User Features

* Register as a beneficiary
* Browse announcements
* Search announcements
* View verified organizations
* Apply to announcements
* Save announcements to favorites
* Receive notifications
* Manage personal profile

### Organization Features

* Register organization accounts
* Upload verification documents
* Publish announcements
* Manage organization profile
* View organization announcements
* Receive application notifications

### Admin Features

* Manage users
* Manage organizations
* Verify organization documents
* Approve or reject organizations
* Approve announcements before publishing
* Block or unblock users and organizations
* Send notifications
* View platform statistics and analytics

### Notifications

* Real-time notification system
* User-specific notifications
* Organization notifications
* System-wide notifications

### Support System

* Submit support requests
* Track support requests
* Admin reply management
* Email notifications

### Favorites

* Save announcements
* Remove announcements from favorites
* View favorite announcements list

### Multilingual Support

* Language switching support
* Current language tracking

---

## User Roles

### Beneficiary

Can browse announcements, apply to opportunities, save favorites, and manage their profile.

### Organization

Can create announcements, manage opportunities, and interact with applicants.

### Admin

Responsible for platform moderation, verification processes, user management, and analytics.

---

## Design Patterns Used

| Pattern         | Usage                                                                   |
| --------------- | ----------------------------------------------------------------------- |
| Observer        | Notification system triggered by user and organization actions          |
| Repository      | Encapsulation of business logic for announcement and support operations |
| Strategy        | Search and filtering mechanisms                                         |
| Factory         | User and organization account creation workflows                        |
| Decorator       | Permission and role-based access control                                |
| Template Method | Shared behavior in profile and resource retrieval views                 |

---

## Tech Stack

**Backend**

* Python
* Django
* Django REST Framework
* Simple JWT

**Frontend**

* React.js

**Database**

* PostgreSQL

**Authentication**

* JWT Authentication

**Deployment**

* Vercel (Frontend)
* PostgreSQL Database

---

## Project Structure

```text
grad-project/
├── api/
├── awn/
├── local/
├── media/
├── organizations/
├── templates/
├── .gitignor
├── compile_translations.py
├── manage.py
├── requirements.txt
└── README.md
```

---

## API Endpoints

### Authentication

| Method | Endpoint                       | Description           |
| ------ | ------------------------------ | --------------------- |
| POST   | /api/auth/signup/user/         | Register beneficiary  |
| POST   | /api/auth/signup/organization/ | Register organization |
| POST   | /api/auth/login/               | Login                 |
| POST   | /api/auth/refresh/             | Refresh JWT token     |
| POST   | /api/auth/logout/              | Logout                |
| GET    | /api/auth/profile/             | Get profile           |
| PATCH  | /api/auth/update-profile/      | Update profile        |
| POST   | /api/auth/forgot-password/     | Forgot password       |
| POST   | /api/auth/reset-password/      | Reset password        |
| POST   | /api/auth/change-password/     | Change password       |

---

### Announcements

| Method | Endpoint                                | Description                       |
| ------ | --------------------------------------- | --------------------------------- |
| GET    | /api/announcements/                     | List announcements                |
| POST   | /api/create-announcements/              | Create announcement               |
| POST   | /api/organizations/create-announcement/ | Organization creates announcement |
| PATCH  | /api/update-announcement/{id}/          | Update announcement               |
| DELETE | /api/delete-announcement/{id}/          | Delete announcement               |
| GET    | /api/announcements/my-announcements/    | Organization announcements        |
| GET    | /api/announcements/pending/             | Pending announcements             |
| PATCH  | /api/announcements/{id}/approve/        | Approve announcement              |

---

### Categories

| Method | Endpoint                      | Description     |
| ------ | ----------------------------- | --------------- |
| GET    | /api/announcement-categories/ | List categories |
| POST   | /api/announcement-categories/ | Create category |

---

### Organizations

| Method | Endpoint                     | Description            |
| ------ | ---------------------------- | ---------------------- |
| GET    | /api/organizations/          | List organizations     |
| GET    | /api/organizations/{id}/     | Organization details   |
| GET    | /api/organizations/verified/ | Verified organizations |
| GET    | /api/organizations/search/   | Search organizations   |

---

### Favorites

| Method | Endpoint                                 | Description     |
| ------ | ---------------------------------------- | --------------- |
| POST   | /api/favorites/add/{announcement_id}/    | Add favorite    |
| DELETE | /api/favorites/remove/{announcement_id}/ | Remove favorite |
| GET    | /api/favorites/                          | List favorites  |

---

### Notifications

| Method | Endpoint                                  | Description                |
| ------ | ----------------------------------------- | -------------------------- |
| GET    | /api/my/notifications/                    | User notifications         |
| POST   | /api/notifications/send-to-user/          | Send notification          |
| POST   | /api/notifications/send-to-users/         | Broadcast to users         |
| POST   | /api/notifications/send-to-organizations/ | Broadcast to organizations |

---

### Support

| Method | Endpoint                       | Description             |
| ------ | ------------------------------ | ----------------------- |
| POST   | /api/support/create/           | Create support request  |
| GET    | /api/support/my-requests/      | My support requests     |
| GET    | /api/support/my-request/{id}/  | Support request details |
| POST   | /api/support/admin/reply/{id}/ | Admin reply             |

---

### Statistics

| Method | Endpoint                          | Description         |
| ------ | --------------------------------- | ------------------- |
| GET    | /api/admin/statistics/            | Platform statistics |
| GET    | /api/admin/statistics/timeseries/ | Analytics over time |

---

## Setup & Installation

```bash
# Clone repository
git clone https://github.com/Feras-Alaqad/grad-project.git

# Navigate into project
cd grad-project

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Run development server
python manage.py runserver
```

## Live Demo

Frontend:

https://awn-platform.vercel.app/ar


## Author

### Feras Alaqad

GitHub:
https://github.com/Feras-Alaqad/

LinkedIn:
https://www.linkedin.com/in/feras-alaqad-804793347

Portfolio:
https://feras-alaqad.netlify.app/
