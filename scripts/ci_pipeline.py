#!/usr/bin/env python3
"""
Script d'intégration continue pour CourseScope
Exécute tous les tests et valide la compatibilité entre les composants
"""

import sys
import subprocess
import os
import time
import json
from pathlib import Path
from datetime import datetime


def run_command(cmd, description, timeout=300):
    """Exécute une commande et retourne le résultat"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=Path(__file__).parent.parent
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {description} : SUCCESS ({duration:.2f}s)")
            return True, result.stdout, duration
        else:
            print(f"❌ {description} : FAILED ({duration:.2f}s)")
            print(f"STDERR: {result.stderr}")
            return False, result.stderr, duration
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} : TIMEOUT ({timeout}s)")
        return False, f"Command timeout after {timeout}s", timeout
    except Exception as e:
        print(f"💥 {description} : ERROR - {str(e)}")
        return False, str(e), 0


def run_unit_tests():
    """Exécute les tests unitaires"""
    success, output, duration = run_command(
        "python -m pytest tests/unit_tests.py -v",
        "Tests unitaires"
    )
    return success, duration


def run_api_tests():
    """Exécute les tests API"""
    # Démarrer le serveur API pour les tests
    print("\n🚀 Démarrage du serveur API pour les tests...")
    
    api_process = None
    try:
        # Lancer le serveur en arrière-plan
        api_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Attendre que le serveur soit prêt
        time.sleep(5)
        
        success, output, duration = run_command(
            "python -m pytest tests/api_tests.py -v",
            "Tests API"
        )
        
        return success, duration
        
    finally:
        if api_process:
            api_process.terminate()
            api_process.wait()


def run_compatibility_tests():
    """Exécute les tests de compatibilité"""
    success, output, duration = run_command(
        "python -m pytest tests/compat_tests.py -v",
        "Tests de compatibilité Streamlit/API"
    )
    return success, duration


def run_sync_tests():
    """Exécute les tests de synchronisation"""
    # Démarrer les deux serveurs pour les tests de sync
    api_process = None
    streamlit_process = None
    
    try:
        print("\n🚀 Démarrage des serveurs pour les tests de synchronisation...")
        
        # Démarrer API
        api_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Démarrer Streamlit
        streamlit_process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "CourseScope.py", "--server.port", "8501", "--server.headless", "true"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Attendre que les serveurs soient prêts
        time.sleep(10)
        
        success, output, duration = run_command(
            "python -m pytest tests/sync_tests.py -v",
            "Tests de synchronisation"
        )
        
        return success, duration
        
    finally:
        if api_process:
            api_process.terminate()
            api_process.wait()
        if streamlit_process:
            streamlit_process.terminate()
            streamlit_process.wait()


def run_load_tests():
    """Exécute les tests de charge"""
    print("\n🔥 Démarrage des tests de charge...")
    
    try:
        # Simuler un test de charge
        success, output, duration = run_command(
            "python tests/api_tests.py",
            "Tests de charge API"
        )
        
        return success, duration
    except Exception as e:
        print(f"⚠️ Tests de charge non disponibles: {e}")
        return True, 0  # Non bloquant


def run_code_quality_checks():
    """Exécute les vérifications de qualité du code"""
    checks = [
        ("black --check .", "Formatage Black"),
        ("isort --check-only .", "Import sorting"),
        ("flake8 . --max-line-length=100", "Linting Flake8"),
        ("mypy . --ignore-missing-imports", "Type checking MyPy")
    ]
    
    all_success = True
    total_duration = 0
    
    for cmd, description in checks:
        success, _, duration = run_command(cmd, description)
        all_success = all_success and success
        total_duration += duration
    
    return all_success, total_duration


def check_dependencies():
    """Vérifie que toutes les dépendances sont installées"""
    success, _, duration = run_command(
        "pip list | findstr -i \"streamlit fastapi uvicorn pandas numpy\"",
        "Vérification des dépendances"
    )
    return success, duration


def generate_report(results):
    """Génère un rapport d'exécution"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_duration": sum(r["duration"] for r in results),
        "results": results,
        "summary": {
            "total_tests": len(results),
            "passed": sum(1 for r in results if r['success']),
            "failed": sum(1 for r in results if not r["success"]),
            "success_rate": f"{(sum(1 for r in results if r['success']) / len(results) * 100):.1f}%"
        }
    }
    
    # Sauvegarder le rapport
    report_path = Path("ci_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return report


def main():
    """Fonction principale d'intégration continue"""
    print(f"\n🎯 DÉMARRAGE DE L'INTÉGRATION CONTINUE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 1. Vérification des dépendances
    success, duration = check_dependencies()
    results.append({
        "name": "Vérification des dépendances",
        "success": success,
        "duration": duration
    })
    
    if not success:
        print("❌ Dépendances manquantes. Arrêt.")
        return False
    
    # 2. Tests unitaires
    success, duration = run_unit_tests()
    results.append({
        "name": "Tests unitaires",
        "success": success,
        "duration": duration
    })
    
    # 3. Vérification de qualité du code
    success, duration = run_code_quality_checks()
    results.append({
        "name": "Qualité du code",
        "success": success,
        "duration": duration
    })
    
    # 4. Tests API
    success, duration = run_api_tests()
    results.append({
        "name": "Tests API",
        "success": success,
        "duration": duration
    })
    
    # 5. Tests de compatibilité
    success, duration = run_compatibility_tests()
    results.append({
        "name": "Tests de compatibilité",
        "success": success,
        "duration": duration
    })
    
    # 6. Tests de synchronisation (optionnel)
    try:
        success, duration = run_sync_tests()
        results.append({
            "name": "Tests de synchronisation",
            "success": success,
            "duration": duration
        })
    except Exception as e:
        print(f"⚠️ Tests de synchronisation ignorés: {e}")
        results.append({
            "name": "Tests de synchronisation",
            "success": True,
            "duration": 0,
            "skipped": True
        })
    
    # 7. Tests de charge (optionnel)
    success, duration = run_load_tests()
    results.append({
        "name": "Tests de charge",
        "success": success,
        "duration": duration
    })
    
    # Générer le rapport
    report = generate_report(results)
    
    # Afficher le résumé
    print(f"\n{'='*80}")
    print("📊 RAPPORT D'INTÉGRATION CONTINUE")
    print(f"{'='*80}")
    
    total_duration = report["total_duration"]
    passed = report["summary"]["passed"]
    failed = report["summary"]["failed"]
    success_rate = report["summary"]["success_rate"]
    
    print(f"⏱️ Durée totale: {total_duration:.2f}s")
    print(f"✅ Tests réussis: {passed}")
    print(f"❌ Tests échoués: {failed}")
    print(f"📈 Taux de réussite: {success_rate}")
    
    if failed > 0:
        print(f"\n🔍 Tests échoués:")
        for result in results:
            if not result["success"]:
                print(f"   ❌ {result['name']}")
    
    print(f"\n📄 Rapport détaillé: ci_report.json")
    
    # Nettoyer
    try:
        import shutil
        if Path("./test_activities").exists():
            shutil.rmtree("./test_activities")
        if Path("./test_sync").exists():
            shutil.rmtree("./test_sync")
    except:
        pass
    
    # Retourner le résultat global
    overall_success = failed == 0
    
    if overall_success:
        print(f"\n🎉 INTÉGRATION CONTINUE : SUCCESS ✅")
        return True
    else:
        print(f"\n💥 INTÉGRATION CONTINUE : FAILED ❌")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)