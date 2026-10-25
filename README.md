# 📚 Smart Library Management System Using QR Code

![Python](https://img.shields.io/badge/Python-3.x-blue)
![IoT](https://img.shields.io/badge/Technology-IoT-green)
![Platform](https://img.shields.io/badge/Platform-Embedded%20Systems-orange)
![Status](https://img.shields.io/badge/Project-Academic%20Project-purple)

## 🚀 Project Overview

The **Smart Library Management System** is an intelligent, technology-driven solution designed to simplify library operations through automation, QR code scanning, and book availability tracking. The project aims to reduce manual paperwork, improve efficiency, and provide a convenient way to manage book issuance and returns.

The system integrates Python-based software modules, a database, QR code generation and scanning, and embedded hardware components to create a smart and organized library management solution.

## 🎯 Objectives

- Automate book issuance and return operations.
- Identify books using unique QR codes.
- Track book availability and maintain library records.
- Reduce manual errors and administrative workload.
- Provide a simple interface for managing library activities.
- Explore the integration of software, databases, and IoT hardware.

## ✨ Key Features

- **QR Code Generation:** Generate unique QR codes for book identification.
- **QR Code Scanning:** Scan book QR codes to identify books and process transactions.
- **Book Management:** Maintain book information and availability records.
- **Database Integration:** Store and manage library information using a database.
- **Graphical User Interface:** Provide a user-friendly interface for library operations.
- **Notifications:** Support notification functionality for relevant library events.
- **Deadline Checking:** Include a module for checking book return deadlines.
- **LCD Communication:** Include a module for interfacing with an LCD display.
- **Modular Architecture:** Separate functionalities into individual Python modules for easier maintenance.

## 🛠️ Technologies Used

- **Programming Language:** Python
- **Database:** SQLite / local database
- **QR Code Processing:** QR code generation and scanning libraries
- **GUI:** Python GUI framework
- **Hardware Integration:** ESP32-CAM, Raspberry Pi Pico W, LCD display, LEDs, and buzzer
- **Development Environment:** Python IDE and Arduino IDE, where applicable

## 📂 Project Structure

```text
Smart-Library-Management-System/
│
├── main.py
├── library_manager.py
├── database.py
├── gui.py
├── qr_generator.py
├── qr_scanner.py
├── deadline_checker.py
├── notification.py
├── serial_comm.py
├── lcd_i2c.py
├── requirements.txt
└── library.db
```

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/nishadamit307-web/Smart-Library-management-system-.git
cd Smart-Library-management-system-
```

### 2. Install Python Dependencies

Make sure Python 3 is installed, then run:

```bash
pip install -r requirements.txt
```

### 3. Run the Application

Check the project's entry-point file and run the appropriate main script:

```bash
python main.py
```

If your project uses a different entry point, run that script instead.

## 🔄 Working Principle

1. Book details are registered and stored in the library database.
2. A unique QR code is generated for each book.
3. The QR code is scanned to identify the selected book.
4. The system checks the book's current availability.
5. The book's issue or return status is updated according to the implemented workflow.
6. The interface displays relevant information, and supported notification or hardware modules provide feedback.

## 🔮 Future Scope

- Cloud-based database integration.
- Student identification and authentication.
- Web-based library dashboard.
- Book search and advanced filtering.
- Automated overdue notifications.
- Transaction history and usage analytics.
- Remote monitoring and centralized library management.

## 🎓 Applications

- Schools and colleges.
- Engineering institute libraries.
- Educational institutions.
- Small community libraries.
- Book inventory and resource management systems.

## 👨‍💻 Developer

**Nishad Amit Subhash**

GitHub: [@nishadamit307-web](https://github.com/nishadamit307-web)

## 🏁 Conclusion

The Smart Library Management System demonstrates how QR code technology, database management, Python programming, and embedded systems can be combined to improve library workflows. The project provides a foundation for developing more efficient, accessible, and scalable library automation solutions.

**⭐ If you find this project useful, consider giving the repository a star!**
