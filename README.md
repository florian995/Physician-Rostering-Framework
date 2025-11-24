# Physician-Rostering-Framework
A General Framework for Physician Rostering Using Mixed-Integer Programming

## 📘 Overview
This project provides a **general mixed-integer programming (MIP) framework** for solving physician rostering problems in hospitals.  
It reads input data from a relational database, formulates and solves the corresponding optimization model, and writes the resulting roster back to the database.  

The framework supports a wide range of constraints and configurations and is designed to be flexible enough for **practical use in real hospital settings**.

---

## ⚙️ Features
- Reads all scheduling data directly from a database.
- Formulates a complete MIP model for physician rostering.
- Solves the optimization problem using the **CBC solver (COIN-OR)**.
- Writes all results back into the database automatically.
- Supports multiple test databases for experimentation and benchmarking.
- Built as a **modular and extensible Python application**.

---

## 🧠 Research Context
This framework was developed as part of a research project at **Technische Universität München (TUM)**.  
Its goal is to create a **generic, configurable, and practical framework** for physician rostering that provides a generic python framework for real-world applicability in various hospitals.

**Authors:**  
- Florian Meier  
- Jan Boeckmann  
- Clemens Thielen
- Optimization and Sustainable Decision Making, Technical University of Munich  

---

## 🚀 Getting Started

### 1. Prerequisites
Before running the framework, ensure that the following components are installed:

- **Python 3.10** or higher  
- **CBC Solver** from [COIN-OR](https://github.com/coin-or/Cbc)
- All required Python libraries listed in the `requirements.txt` file  

### 2. Running
Run python main.py.
The program automatically connects to the database located in the same directory as main.py.

### 3. Test other instances
The folder databases/ contains additional test and benchmark instances.
To use one of these databases, copy the desired file to the main directory (where main.py is located) and replace the existing database.
The program will then use this database automatically.

Visit the [wiki](https://github.com/florian995/Physician-Rostering-Framework/wiki) for more detailed information.
