"""
Sistema de Gestión de Empleados Refactorizado
Aplicando principios SOLID y patrones de diseño

Camila Alejandra Melara Liévano 20235691 
Daniela Rocío Pineda Pineda 20235662 
Diego Enrique Morales Zepeda 20235780 
Genesis Beraly Parada Ventura 20235861 
Ximena Sarai Zelaya Salazar 20235973 

"""

import os
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


# ==================== ENUMS Y CONSTANTES ====================

"Roles de posibles empleados"
class EmployeeRole(Enum):
    INTERN = "intern"
    MANAGER = "manager"
    VICE_PRESIDENT = "vice_president"
    DEVELOPER = "developer"

"Tipo de contrato de empleado"
class EmployeeType(Enum):
    SALARIED = "salaried"
    HOURLY = "hourly"
    FREELANCER = "freelancer"

"Tipo de transacción que se puede hacer al historial de un empleado"
class TransactionType(Enum):
    VACATION = "vacation"
    VACATION_PAYOUT = "vacation_payout"
    PAYMENT = "payment"
    BONUS = "bonus"


# ==================== CONFIGURACIÓN (SINGLETON) ====================

class ConfigLoader:
    "Singleton para cargar configuraciones desde archivo JSON"
    _instance = None
    _config = None

    "Controla que haya una sola instancia de la clase"
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._load_config()

    "Carga configuración desde config.json"
    def _load_config(self):
        default_config = {
            "vacation": {
                "default_days": 25,
                "payout_days": 5,
                "policies": {
                    "intern": {"can_take": False, "can_payout": False},
                    "manager": {"can_take": True, "can_payout": True, "max_payout": 10},
                    "vice_president": {"can_take": True, "can_payout": True, "max_per_request": 5}
                }
            },
            "payment": {
                "default_hourly_rate": 50,
                "default_monthly_salary": 5000,
                "bonus": {
                    "salaried_percentage": 0.10,
                    "hourly_bonus_amount": 100,
                    "hourly_hours_threshold": 160
                }
            }
        }
        
        try:
            with open('config.json', 'r') as f:
                self._config = json.load(f)
        except FileNotFoundError:
            self._config = default_config
            # Crear archivo config.json con configuración por defecto
            with open('config.json', 'w') as f:
                json.dump(default_config, f, indent=2)

    "Obtiene un valor de configuración usando notación de punto"
    def get(self, key_path: str):
        keys = key_path.split('.')
        value = self._config
        for key in keys:
            value = value.get(key, {})
        return value


# ==================== MODELOS DE DATOS ====================

"Representa una transacción en el historial"
@dataclass
class Transaction:
    employee_name: str
    transaction_type: TransactionType
    amount: float
    description: str
    date: datetime = field(default_factory=datetime.now)


# ==================== ESTRATEGIAS DE PAGO (STRATEGY PATTERN) ====================

"Cálculo de pagos (abstracta)"
class PaymentStrategy(ABC):
    @abstractmethod
    def calculate_payment(self, employee: 'Employee') -> float:
        pass

"Pago para empleados asalariados"
class SalariedPaymentStrategy(PaymentStrategy):
    def calculate_payment(self, employee: 'Employee') -> float:
        config = ConfigLoader()
        base_salary = getattr(employee, 'monthly_salary', 
                            config.get('payment.default_monthly_salary'))
        return base_salary

"Pago para empleados por horas"
class HourlyPaymentStrategy(PaymentStrategy):
    def calculate_payment(self, employee: 'Employee') -> float:
        hourly_rate = getattr(employee, 'hourly_rate', 0)
        hours = getattr(employee, 'hours_worked', 0)
        return hourly_rate * hours

"Estrategia de pago para freelancers"
class FreelancerPaymentStrategy(PaymentStrategy):
    def calculate_payment(self, employee: 'Employee') -> float:
        projects = getattr(employee, 'projects', [])
        return sum(project.get('amount', 0) for project in projects)


# ==================== ESTRATEGIAS DE BONIFICACIÓN ====================

"Estrategia abstracta para cálculo de bonificaciones"
class BonusStrategy(ABC):
    @abstractmethod
    def calculate_bonus(self, employee: 'Employee', base_payment: float) -> float:
        pass

"Bonificación para empleados asalariados"
class SalariedBonusStrategy(BonusStrategy):
    def calculate_bonus(self, employee: 'Employee', base_payment: float) -> float:
        config = ConfigLoader()
        percentage = config.get('payment.bonus.salaried_percentage')
        return base_payment * percentage

"Bonificación para empleados por horas"
class HourlyBonusStrategy(BonusStrategy):
    def calculate_bonus(self, employee: 'Employee', base_payment: float) -> float:
        config = ConfigLoader()
        hours = getattr(employee, 'hours_worked', 0)
        threshold = config.get('payment.bonus.hourly_hours_threshold')
        bonus_amount = config.get('payment.bonus.hourly_bonus_amount')
        
        return bonus_amount if hours > threshold else 0


"Sin bonificación (para pasantes y freelancers)"
class NoBonus(BonusStrategy):
    def calculate_bonus(self, employee: 'Employee', base_payment: float) -> float:
        return 0

"Bonificación adicional por desempeño"
class PerformanceBonusStrategy(BonusStrategy):
    def calculate_bonus(self, employee: 'Employee', base_payment: float) -> float:
        config = ConfigLoader()
        performance_rates = config.get('payment.bonus.performance')

        emp_type_key = employee.employee_type.value  # salaried, hourly, freelancer
        performance_rate = performance_rates.get(emp_type_key, 0)

        return base_payment * performance_rate

"""Junta las clases, para poder dar bonos extra, "SalariedBonusStrategy", "HourlyBonusStrategy" y "PerformanceBonusStrategy" en una clase "CombinedBonusStrategy"""
class CombinedBonusStrategy(BonusStrategy):
    def __init__(self, base_bonus: BonusStrategy, extra_bonus: BonusStrategy):
        self.base_bonus = base_bonus
        self.extra_bonus = extra_bonus

    def calculate_bonus(self, employee, base_payment):
        return self.base_bonus.calculate_bonus(employee, base_payment) + \
               self.extra_bonus.calculate_bonus(employee, base_payment)

# ==================== POLÍTICAS DE VACACIONES ====================

"Política abstracta para manejo de vacaciones"
class VacationPolicy(ABC):

    @abstractmethod
    def can_take_vacation(self, employee: 'Employee', days: int = 1) -> bool:
        pass
    
    @abstractmethod
    def can_take_payout(self, employee: 'Employee', days: int) -> bool:
        pass
    
    @abstractmethod
    def process_vacation(self, employee: 'Employee', payout: bool, days: int = None) -> str:
        pass

class InternVacationPolicy(VacationPolicy):
    
    def can_take_vacation(self, employee: 'Employee', days: int = 1) -> bool:
        return False
    
    def can_take_payout(self, employee: 'Employee', days: int) -> bool:
        return False
    
    def process_vacation(self, employee: 'Employee', payout: bool, days: int = None) -> str:
        return "Los pasantes no pueden solicitar vacaciones ni compensación monetaria."

class ManagerVacationPolicy(VacationPolicy):
    
    def can_take_vacation(self, employee: 'Employee', days: int = 1) -> bool:
        return employee.vacation_days >= days
    
    def can_take_payout(self, employee: 'Employee', days: int) -> bool:
        config = ConfigLoader()
        max_payout = config.get('vacation.policies.manager.max_payout')
        return employee.vacation_days >= days and days <= max_payout
    
    def process_vacation(self, employee: 'Employee', payout: bool, days: int = None) -> str:
        if payout:
            days = days or ConfigLoader().get('vacation.payout_days')
            if self.can_take_payout(employee, days):
                employee.vacation_days -= days
                return f"Payout de {days} días procesado. Días restantes: {employee.vacation_days}"
            else:
                return f"No se puede procesar el payout. Días disponibles: {employee.vacation_days}"
        else:
            if self.can_take_vacation(employee, 1):
                employee.vacation_days -= 1
                return f"Vacación procesada. Días restantes: {employee.vacation_days}"
            else:
                return "No hay suficientes días de vacaciones disponibles."

class VicePresidentVacationPolicy(VacationPolicy):
    
    def can_take_vacation(self, employee: 'Employee', days: int = 1) -> bool:
        config = ConfigLoader()
        max_per_request = config.get('vacation.policies.vice_president.max_per_request')
        return days <= max_per_request  # Vacaciones ilimitadas pero máximo 5 por solicitud
    
    def can_take_payout(self, employee: 'Employee', days: int) -> bool:
        return employee.vacation_days >= days
    
    def process_vacation(self, employee: 'Employee', payout: bool, days: int = None) -> str:
        if payout:
            days = days or ConfigLoader().get('vacation.payout_days')
            if self.can_take_payout(employee, days):
                employee.vacation_days -= days
                return f"Payout de {days} días procesado. Días restantes: {employee.vacation_days}"
            else:
                return f"No se puede procesar el payout. Días disponibles: {employee.vacation_days}"
        else:
            if self.can_take_vacation(employee, 1):
                employee.vacation_days -= 1
                return f"Vacación procesada. Días restantes: {employee.vacation_days}"
            else:
                return "Máximo 5 días por solicitud para vicepresidentes."

class DeveloperVacationPolicy(VacationPolicy):

    def can_take_vacation(self, employee: 'Employee', days: int = 1) -> bool:
        config = ConfigLoader()
        max_per_request = config.get('vacation.policies.developer.max_per_request')
        return employee.vacation_days >= days and days <= max_per_request

    def can_take_payout(self, employee: 'Employee', days: int) -> bool:
        config = ConfigLoader()
        max_payout = config.get('vacation.policies.developer.max_payout')
        return employee.vacation_days >= days and days <= max_payout

    def process_vacation(self, employee: 'Employee', payout: bool, days: int = None) -> str:
        config = ConfigLoader()
        if payout:
            days = days or config.get('vacation.payout_days')
            if self.can_take_payout(employee, days):
                employee.vacation_days -= days
                return f"Payout de {days} días procesado. Días restantes: {employee.vacation_days}"
            else:
                return f"No se puede procesar el payout. Días disponibles: {employee.vacation_days}"
        else:
            days = days or 1
            if self.can_take_vacation(employee, days):
                employee.vacation_days -= days
                return f"Vacación de {days} días procesada. Días restantes: {employee.vacation_days}"
            else:
                return "No cumple con los requisitos para la solicitud de vacaciones."

# ==================== FACTORY PARA EMPLEADOS ====================

"Factory Method para crear empleados con sus estrategias"
class EmployeeFactory:

    @staticmethod
    def create_employee(name: str, role: EmployeeRole, emp_type: EmployeeType, **kwargs) -> 'Employee':
        """Crea un empleado con las estrategias apropiadas"""
        config = ConfigLoader()

        # Crear empleado base
        vac_days = 0 if role == EmployeeRole.INTERN or emp_type == EmployeeType.FREELANCER \
            else config.get('vacation.default_days')

        employee = Employee(
            name=name,
            role=role,
            vacation_days=vac_days
        )

        # Asignar estrategias según el tipo
        if emp_type == EmployeeType.SALARIED:
            employee.monthly_salary = kwargs.get('monthly_salary', config.get('payment.default_monthly_salary'))
            payment_strategy = SalariedPaymentStrategy()
            base_bonus = SalariedBonusStrategy()
            perf_bonus = PerformanceBonusStrategy()
            bonus_strategy = CombinedBonusStrategy(base_bonus, perf_bonus)

        elif emp_type == EmployeeType.HOURLY:
            employee.hourly_rate = kwargs.get('hourly_rate', config.get('payment.default_hourly_rate'))
            employee.hours_worked = kwargs.get('hours_worked', 0)
            payment_strategy = HourlyPaymentStrategy()
            base_bonus = HourlyBonusStrategy()
            perf_bonus = PerformanceBonusStrategy()
            bonus_strategy = CombinedBonusStrategy(base_bonus, perf_bonus)

        elif emp_type == EmployeeType.FREELANCER:
            employee.projects = kwargs.get('projects', [])
            payment_strategy = FreelancerPaymentStrategy()
            bonus_strategy = PerformanceBonusStrategy()

        # Asignar estrategias
        employee.payment_strategy = payment_strategy
        employee.bonus_strategy = bonus_strategy

        # Asignar política de vacaciones según el rol
        if role == EmployeeRole.INTERN:
            employee.vacation_policy = InternVacationPolicy()
            employee.bonus_strategy = NoBonus()  # Los pasantes no reciben bonos

        elif role == EmployeeRole.MANAGER:
            employee.vacation_policy = ManagerVacationPolicy()

        elif role == EmployeeRole.VICE_PRESIDENT:
            employee.vacation_policy = VicePresidentVacationPolicy()
        elif role == EmployeeRole.DEVELOPER:
            employee.vacation_policy = DeveloperVacationPolicy()

        employee.employee_type = emp_type
        return employee


# ==================== MODELO EMPLOYEE REFACTORIZADO ====================

@dataclass
class Employee:
    "Empleado con estrategias inyectadas"
    name: str
    role: EmployeeRole
    vacation_days: int = 25
    payment_strategy: PaymentStrategy = None
    bonus_strategy: BonusStrategy = None
    vacation_policy: VacationPolicy = None
    employee_type: EmployeeType = None
    
    def calculate_payment(self) -> float:
        "Calcula el pago base usando la estrategia asignada"
        return self.payment_strategy.calculate_payment(self)
    
    def calculate_bonus(self) -> float:
        "Calcula la bonificación usando la estrategia asignada"
        base_payment = self.calculate_payment()
        return self.bonus_strategy.calculate_bonus(self, base_payment)
    
    def calculate_total_payment(self) -> float:
        "Calcula el pago total incluyendo bonificaciones"
        return self.calculate_payment() + self.calculate_bonus()
    
    def request_vacation(self, payout: bool = False, days: int = None) -> str:
        "Solicita vacaciones usando la política asignada"
        return self.vacation_policy.process_vacation(self, payout, days)


# ==================== COMANDOS (COMMAND PATTERN) ====================

"Comando abstracto"
class Command(ABC):
    
    @abstractmethod
    def execute(self) -> Any:
        pass

"Comando para pagar a un empleado"
class PayEmployeeCommand(Command):
    
    def __init__(self, employee: Employee, transaction_history: List[Transaction]):
        self.employee = employee
        self.transaction_history = transaction_history
    
    def execute(self) -> str:
        total_payment = self.employee.calculate_total_payment()
        bonus = self.employee.calculate_bonus()
        
        # Registrar transacción de pago
        payment_transaction = Transaction(
            employee_name=self.employee.name,
            transaction_type=TransactionType.PAYMENT,
            amount=total_payment,
            description=f"Pago total: ${total_payment:.2f}"
        )
        self.transaction_history.append(payment_transaction)
        
        # Registrar bonificación si aplica
        if bonus > 0:
            bonus_transaction = Transaction(
                employee_name=self.employee.name,
                transaction_type=TransactionType.BONUS,
                amount=bonus,
                description=f"Bonificación: ${bonus:.2f}"
            )
            self.transaction_history.append(bonus_transaction)
        
        return f"Pagando a {self.employee.name}: ${total_payment:.2f} (incluye bonificación: ${bonus:.2f})"

"Comando para procesar vacaciones"
class VacationCommand(Command):
    
    def __init__(self, employee: Employee, payout: bool, transaction_history: List[Transaction], days: int = None):
        self.employee = employee
        self.payout = payout
        self.transaction_history = transaction_history
        self.days = days
    
    def execute(self) -> str:
        result = self.employee.request_vacation(self.payout, self.days)
        
        # Registrar transacción si fue exitosa
        if "procesado" in result or "procesada" in result:
            transaction_type = TransactionType.VACATION_PAYOUT if self.payout else TransactionType.VACATION
            days_used = self.days or (ConfigLoader().get('vacation.payout_days') if self.payout else 1)
            
            transaction = Transaction(
                employee_name=self.employee.name,
                transaction_type=transaction_type,
                amount=days_used,
                description=result
            )
            self.transaction_history.append(transaction)
        
        return result


# ==================== DECORADOR PARA LOGGING ====================

"Decorador para agregar logging a operaciones"
class LoggingDecorator:
    
    def __init__(self, command: Command):
        self.command = command
    
    def execute(self) -> Any:
        result = self.command.execute()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[LOG {timestamp}] {result}")
        return result


# ==================== COMPANY REFACTORIZADA ====================

"Compañía con arquitectura mejorada"
class Company:
    
    def __init__(self):
        self.employees: List[Employee] = []
        self.transaction_history: List[Transaction] = []
    
    def add_employee(self, employee: Employee) -> None:
        "Agrega un empleado a la compañía"
        self.employees.append(employee)
    
    def find_employees_by_role(self, role: EmployeeRole) -> List[Employee]:
        "Encuentra empleados por rol (método genérico)"
        return [emp for emp in self.employees if emp.role == role]
    
    def find_managers(self) -> List[Employee]:
        "Encuentra gerentes"
        return self.find_employees_by_role(EmployeeRole.MANAGER)
    
    def find_interns(self) -> List[Employee]:
        "Encuentra pasantes"
        return self.find_employees_by_role(EmployeeRole.INTERN)
    
    def find_vice_presidents(self) -> List[Employee]:
        "Encuentra vicepresidentes"
        return self.find_employees_by_role(EmployeeRole.VICE_PRESIDENT)
    
    def pay_employee(self, employee: Employee) -> str:
        "Paga a un empleado usando Command pattern"
        command = PayEmployeeCommand(employee, self.transaction_history)
        logged_command = LoggingDecorator(command)
        return logged_command.execute()
    
    def pay_all_employees(self) -> None:
        "Paga a todos los empleados"
        for employee in self.employees:
            self.pay_employee(employee)
    
    def process_vacation(self, employee: Employee, payout: bool = False, days: int = None) -> str:
        "Procesa vacaciones"
        command = VacationCommand(employee, payout, self.transaction_history, days)
        logged_command = LoggingDecorator(command)
        return logged_command.execute()
    
    def get_employee_history(self, employee_name: str) -> List[Transaction]:
        "Obtiene el historial de transacciones de un empleado"
        return [t for t in self.transaction_history if t.employee_name == employee_name]


# ==================== INTERFAZ DE USUARIO ====================

"Interfaz de usuario separada de la lógica de negocio"
class EmployeeManagementUI:
    
    def __init__(self):
        self.company = Company()
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_main_menu(self):
        print("--- Employee Management Menu ---")
        print("1. Create employee")
        print("2. View employees")
        print("3. Grant vacation to an employee")
        print("4. Pay employees")
        print("5. View employee history")
        print("6. Exit")
    
    def create_employee_menu(self):
        try:
            name = input("Employee name: ")
            
            print("Available roles:")
            for i, role in enumerate(EmployeeRole, 1):
                print(f"{i}. {role.value}")
            role_choice = int(input("Select role: "))
            role = list(EmployeeRole)[role_choice - 1]
            
            print("Available types:")
            for i, emp_type in enumerate(EmployeeType, 1):
                print(f"{i}. {emp_type.value}")
            type_choice = int(input("Select type: "))
            emp_type = list(EmployeeType)[type_choice - 1]
            
            kwargs = {}
            if emp_type == EmployeeType.SALARIED:
                kwargs['monthly_salary'] = float(input("Monthly salary: "))
            elif emp_type == EmployeeType.HOURLY:
                kwargs['hourly_rate'] = float(input("Hourly rate: "))
                kwargs['hours_worked'] = int(input("Hours worked: "))
            elif emp_type == EmployeeType.FREELANCER:
                projects = []
                try:
                    total = int(input("¿Cuántos proyectos deseas agregar? "))
                    for i in range(total):
                        print(f"\nProyecto #{i + 1}")
                        nombre = input("Nombre del proyecto: ")
                        monto = float(input("Monto del proyecto ($): "))
                        projects.append({"name": nombre, "amount": monto})
                    kwargs['projects'] = projects
                except ValueError:
                    print("Entrada inválida. No se agregaron proyectos.")
                    kwargs['projects'] = []
            
            employee = EmployeeFactory.create_employee(name, role, emp_type, **kwargs)
            self.company.add_employee(employee)
            print("Employee created successfully!")
            
        except (ValueError, IndexError) as e:
            print(f"Error creating employee: {e}")
    
    def view_employees_menu(self):
        while True:
            self.clear_screen()
            print("--- View Employees Submenu ---")
            print("1. View managers")
            print("2. View interns") 
            print("3. View vice presidents")
            print("4. View all employees")
            print("0. Return to main menu")
            
            choice = input("Select an option: ")
            
            if choice == "1":
                employees = self.company.find_managers()
                self._display_employees(employees, "Managers")
            elif choice == "2":
                employees = self.company.find_interns()
                self._display_employees(employees, "Interns")
            elif choice == "3":
                employees = self.company.find_vice_presidents()
                self._display_employees(employees, "Vice Presidents")
            elif choice == "4":
                self._display_employees(self.company.employees, "All Employees")
            elif choice == "0":
                break
            else:
                print("Invalid option.")
            
            input("Press Enter to continue...")
    
    def _display_employees(self, employees: List[Employee], title: str):
        print(f"\n--- {title} ---")
        if not employees:
            print("No employees found.")
            return
        
        for emp in employees:
            print(f"{emp.name} ({emp.role.value}, {emp.employee_type.value}) - {emp.vacation_days} vacation days")
    
    def vacation_menu(self):
        if not self.company.employees:
            print("No employees available.")
            return
        
        print("Select employee:")
        for idx, emp in enumerate(self.company.employees):
            print(f"{idx}. {emp.name} ({emp.role.value}) - {emp.vacation_days} vacation days")
        
        try:
            idx = int(input("Select employee index: "))
            employee = self.company.employees[idx]
            payout = input("Payout instead of time off? (y/n): ").lower() == "y"

            days_input = input("How many days? (leave empty for default): ")
            days = int(days_input) if days_input.strip() else None

            result = self.company.process_vacation(employee, payout, days)
            print(result)
            
        except (IndexError, ValueError) as e:
            print(f"Error: {e}")
    
    def pay_employees_menu(self):
        if not self.company.employees:
            print("No employees available.")
            return
        
        print("Paying all employees:")
        self.company.pay_all_employees()
    
    def employee_history_menu(self):
        if not self.company.employees:
            print("No employees available.")
            return
        
        print("Select employee:")
        for idx, emp in enumerate(self.company.employees):
            print(f"{idx}. {emp.name}")
        
        try:
            idx = int(input("Select employee index: "))
            employee = self.company.employees[idx]
            history = self.company.get_employee_history(employee.name)
            
            print(f"\n--- Transaction History for {employee.name} ---")
            if not history:
                print("No transactions found.")
                return
            
            for transaction in sorted(history, key=lambda x: x.date, reverse=True):
                print(f"{transaction.date.strftime('%Y-%m-%d %H:%M')} - "
                      f"{transaction.transaction_type.value}: {transaction.description}")
                
        except (IndexError, ValueError) as e:
            print(f"Error: {e}")
    
    def run(self):
        while True:
            self.clear_screen()
            self.display_main_menu()
            
            choice = input("Select an option: ")
            
            if choice == "1":
                self.create_employee_menu()
            elif choice == "2":
                self.view_employees_menu()
            elif choice == "3":
                self.vacation_menu()
            elif choice == "4":
                self.pay_employees_menu()
            elif choice == "5":
                self.employee_history_menu()
            elif choice == "6":
                print("Goodbye!")
                break
            else:
                print("Invalid option.")
            
            if choice != "2":  # El submenu de view ya tiene su propio "Press Enter"
                input("Press Enter to continue...")


# ==================== PUNTO DE ENTRADA ====================

def main():
    "Función principal"
    app = EmployeeManagementUI()
    app.run()


if __name__ == "__main__":
    main()