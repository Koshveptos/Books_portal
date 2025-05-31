"""
Основной файл для запуска всех тестов
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Dict


def run_pytest_tests() -> Dict:
    """Запуск pytest тестов с отчетом о покрытии"""
    print("\n=== Запуск модульных и интеграционных тестов ===")

    # Запуск pytest с отчетом о покрытии
    result = subprocess.run(
        ["pytest", "--cov=app", "--cov-report=term-missing", "--cov-report=html", "-v", "unit/", "integration/"],
        capture_output=True,
        text=True,
    )

    return {"output": result.stdout, "error": result.stderr, "return_code": result.returncode}


def run_load_tests() -> Dict:
    """Запуск нагрузочных тестов с помощью locust"""
    print("\n=== Запуск нагрузочных тестов ===")

    # Запуск locust в headless режиме
    result = subprocess.run(
        [
            "locust",
            "--headless",
            "--users",
            "100",
            "--spawn-rate",
            "10",
            "--run-time",
            "1m",
            "--host",
            "http://localhost:8000",
            "-f",
            "load/locustfile.py",
        ],
        capture_output=True,
        text=True,
    )

    return {"output": result.stdout, "error": result.stderr, "return_code": result.returncode}


def run_security_tests() -> Dict:
    """Запуск тестов безопасности"""
    print("\n=== Запуск тестов безопасности ===")

    # Запуск тестов безопасности
    result = subprocess.run(["pytest", "-v", "security/"], capture_output=True, text=True)

    return {"output": result.stdout, "error": result.stderr, "return_code": result.returncode}


def generate_report(test_results: Dict[str, Dict]) -> None:
    """Генерация отчета о тестировании"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = "test_reports"
    os.makedirs(report_dir, exist_ok=True)

    report = {"timestamp": timestamp, "results": test_results}

    report_path = os.path.join(report_dir, f"test_report_{timestamp}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nОтчет сохранен в: {report_path}")


def main():
    """Основная функция запуска всех тестов"""
    print("=== Начало тестирования ===")
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Запуск всех типов тестов
    test_results = {
        "unit_and_integration": run_pytest_tests(),
        "load": run_load_tests(),
        "security": run_security_tests(),
    }

    # Генерация отчета
    generate_report(test_results)

    # Проверка результатов
    all_passed = all(result["return_code"] == 0 for result in test_results.values())

    print("\n=== Результаты тестирования ===")
    for test_type, result in test_results.items():
        status = "ПРОЙДЕН" if result["return_code"] == 0 else "НЕ ПРОЙДЕН"
        print(f"{test_type}: {status}")
        if result["error"]:
            print(f"Ошибки:\n{result['error']}")

    print(f"\nВремя окончания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Общий результат: {'ПРОЙДЕН' if all_passed else 'НЕ ПРОЙДЕН'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
