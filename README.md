# ResQLink - Disaster Management & Resource Distribution System

**ResQLink** is a comprehensive web-based platform designed to facilitate rapid and organized response during emergencies. It integrates Admins, NGOs, Volunteers, and Affected Individuals to ensure efficient coordination of rescue operations and the delivery of essential resources like food, water, and medical supplies.

##  Technologies Used
* **Backend:** Python (Django)
* **Database:** MySQL
* **Frontend:** HTML, CSS, Bootstrap, JavaScript
* **Version Control:** Git & GitHub

##  Key Features

### 1.  Admin Module (Central Command)
* **User Management:** Approve, reject, or block NGO and Volunteer registrations.
* **Resource Coordination:** Manage resource categories (Food, Water, Clothing) and location data.
* **Smart Assignment:** Assign requests to NGOs/Volunteers based on proximity and resource availability.
* **Split Assignments:** Automatically split a large request across multiple NGOs if one cannot fulfill it entirely.
* **Broadcast System:** Send urgent alerts to all registered NGOs/Volunteers when resources are insufficient.
* **Reporting:** Generate analytics reports on requests, resources, and stakeholder performance.

### 2.  NGO Module
* **Stock Management:** Update resource availability and stock levels in real-time.
* **Request Handling:** View, accept, or decline assigned disaster requests.
* **Status Tracking:** Update the status of relief operations (In-Progress/Completed).

### 3.  Volunteer Module
* **Portfolio Verification:** Register with a portfolio for Admin verification.
* **Availability Status:** Toggle status between Free, Busy, or Offline.
* **Task Execution:** Accept delivery tasks and update delivery status.

### 4.  Public / Victim Module
* **No Registration Required:** Affected individuals can submit urgent requests without a complex sign-up process.
* **Request Tracking:** Track the status of their help requests (Pending, Assigned, Completed).

##  How to Run this Project

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/sandra7145dev-cloud/ResQlink.git](https://github.com/sandra7145dev-cloud/ResQlink.git)
    cd ResQlink
    ```

2.  **Create Virtual Environment**
    ```bash
    python -m venv venv
    # Activate:
    # Windows: venv\Scripts\activate
    # Mac/Linux: source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install django mysqlclient
    ```

4.  **Database Configuration**
    * Create a database named `db_resqlink` in MySQL.
    * Update `settings.py` with your MySQL credentials.

5.  **Run Migrations & Server**
    ```bash
    python manage.py migrate
    python manage.py runserver
    ```

---
