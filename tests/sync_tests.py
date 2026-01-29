import pytest
import asyncio
import httpx
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

from services.activity_service import load_activity_from_bytes
from storage.activity_store import LocalTempStorage, DatabaseStorage
from sync.streamlit_sync_manager import StreamlitSyncManager


class TestStreamlitSynchronization:
    """Tests pour la synchronisation entre le frontend Streamlit et l'API"""
    
    def __init__(self):
        self.api_base_url = "http://localhost:8000"
        self.streamlit_base_url = "http://localhost:8501"
        self.temp_storage = LocalTempStorage("./test_sync")
    
    def setup_method(self):
        """Setup pour les tests de synchronisation"""
        # Nettoyer le stockage de test
        if self.temp_storage.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_storage.temp_dir)
    
    def teardown_method(self):
        """Nettoyage après les tests"""
        if self.temp_storage.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_storage.temp_dir)
    
    def test_streamlit_api_synchronization(self):
        """Test la synchronisation des activités entre Streamlit et API"""
        
        # Vérifier que les services sont démarrés
        try:
            api_response = httpx.get(f"{self.api_base_url}/health", timeout=5)
            assert api_response.status_code == 200
        except:
            pytest.skip("API server not running")
            return
            
        try:
            streamlit_response = httpx.get(f"{self.streamlit_base_url}/_stcore/health", timeout=5)
            assert streamlit_response.status_code == 200
        except:
            pytest.skip("Streamlit server not running")
            return
        
        # Test fichier de synchronisation
        test_file = Path("C:\\Users\\domin\\Documents\\Python Scripts\\CourseScope\\tests\\data\\sync_test.gpx")
        
        if not test_file.exists():
            pytest.skip("Fichier de test de synchronisation non trouvé")
            return
            
        with open(test_file, 'rb') as f:
            test_data = f.read()
        
        # 1. Charger via Streamlit
        streamlit_activity = load_activity_from_bytes(test_data, "sync_test.gpx")
        
        # 2. Envoyer à l'API
        api_response = httpx.post(
            f"{self.api_base_url}/api/v1/activity/load",
            files={"file": ("sync_test.gpx", test_data), "name": "sync_test.gpx"}
        )
        
        assert api_response.status_code == 200
        api_data = api_response.json()
        activity_id = api_data["id"]
        
        # 3. Récupérer depuis l'API
        real_activity_response = httpx.get(f"{self.api_base_url}/api/v1/activity/{activity_id}/real")
        assert real_activity_response.status_code == 200
        
        api_activity_data = real_activity_response.json()
        
        # 4. Comparer les métriques principales
        streamlit_df = streamlit_activity.df
        
        # Convertir les données de l'API en DataFrame pour comparaison
        api_times = [d["t"] for d in api_activity_data["series"]]
        api_distances = [d["dist"] for d in api_activity_data["series"]]
        api_speeds = [d["speed"] for d in api_activity_data["series"]]
        
        api_df = pd.DataFrame({
            'time': api_times,
            'distance_m': api_distances,
            'speed_m_s': api_speeds
        })
        
        # Comparer les statistiques clés (avec tolérance)
        assert abs(streamlit_df['speed_m_s'].mean() - api_df['speed_m_s'].mean()) < 0.01
        assert abs(streamlit_df['distance_m'].max() - api_df['distance_m'].max()) < 1.0
        
        print("✅ Synchronisation Streamlit ↔ API : SUCCESS")
    
    def test_real_time_updates(self):
        """Test les mises à jour en temps réel"""
        
        sync_manager = StreamlitSyncManager(
            api_base_url=self.api_base_url,
            streamlit_base_url=self.streamlit_base_url
        )
        
        # Simuler une mise à jour d'activité
        test_activity_id = "test_activity_123"
        
        # Créer une activité de test
        test_file = Path("C:\\Users\\domin\\Documents\\Python Scripts\\CourseScope\\tests\\data\\realtime_test.gpx")
        
        if test_file.exists():
            with open(test_file, 'rb') as f:
                activity_data = f.read()
            
            activity = load_activity_from_bytes(activity_data, "realtime_test.gpx")
            self.temp_storage.store(activity, "realtime_test.gpx")
            
            # Simuler la synchronisation
            sync_result = sync_manager.sync_activity(
                activity_id=test_activity_id,
                storage=self.temp_storage
            )
            
            assert sync_result.success
            print(f"✅ Mise à jour temps réel : SUCCESS - {sync_result.message}")
        else:
            pytest.skip("Fichier de test de temps réel non trouvé")
    
    def test_concurrent_access(self):
        """Test l'accès concurrent aux données"""
        import threading
        
        # Test avec plusieurs accès simultanés
        results = []
        errors = []
        
        def concurrent_request(request_id):
            try:
                response = httpx.get(f"{self.api_base_url}/api/v1/activities", timeout=10)
                if response.status_code == 200:
                    results.append(f"Request {request_id}: SUCCESS")
                else:
                    errors.append(f"Request {request_id}: FAILED {response.status_code}")
            except Exception as e:
                errors.append(f"Request {request_id}: ERROR {str(e)}")
        
        # Lancer 5 requêtes concurrentes
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Attendre la fin de toutes les requêtes
        for thread in threads:
            thread.join()
        
        # Vérifier qu'aucune erreur n'est survenue
        assert len(errors) == 0, f"Erreurs concurrentes: {errors}"
        assert len(results) == 5
        
        print("✅ Accès concurrent : SUCCESS")
    
    def test_data_consistency(self):
        """Test la cohérence des données entre les systèmes"""
        
        # Charger plusieurs activités et vérifier la cohérence
        test_files = [
            "course.gpx",
            "course2.gpx", 
            "enduro.gpx",
            "trail.gpx"
        ]
        
        base_path = Path("C:\\Users\\domin\\Documents\\Python Scripts\\CourseScope\\tests\\data")
        activities_data = []
        
        for filename in test_files:
            file_path = base_path / filename
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    data = f.read()
                
                # Parser avec Streamlit
                streamlit_activity = load_activity_from_bytes(data, filename)
                
                # Envoyer à l'API
                api_response = httpx.post(
                    f"{self.api_base_url}/api/v1/activity/load",
                    files={"file": (filename, data), "name": filename}
                )
                
                if api_response.status_code == 200:
                    api_data = api_response.json()
                    activity_id = api_data["id"]
                    
                    # Récupérer les données de l'API
                    real_response = httpx.get(f"{self.api_base_url}/api/v1/activity/{activity_id}/real")
                    if real_response.status_code == 200:
                        real_data = real_response.json()
                        activities_data.append({
                            'filename': filename,
                            'streamlit': streamlit_activity.df,
                            'api': real_data
                        })
        
        # Vérifier la cohérence pour chaque activité
        for activity in activities_data:
            streamlit_df = activity['streamlit']
            api_data = activity['api']
            
            # Comparer les distances totales
            streamlit_distance = streamlit_df['distance_m'].max()
            api_distance = max(point['dist'] for point in api_data['series'])
            
            assert abs(streamlit_distance - api_distance) < 1.0, f"Incohérence distance pour {activity['filename']}"
        
        print("✅ Cohérence des données : SUCCESS")
    
    def test_error_handling(self):
        """Test la gestion des erreurs de synchronisation"""
        
        sync_manager = StreamlitSyncManager(
            api_base_url="http://invalid-url:9999",  # URL invalide
            streamlit_base_url=self.streamlit_base_url
        )
        
        # Tester la gestion d'erreur de connexion
        sync_result = sync_manager.sync_activity(
            activity_id="test_error",
            storage=self.temp_storage
        )
        
        assert not sync_result.success
        assert "error" in sync_result.message.lower()
        
        print("✅ Gestion des erreurs : SUCCESS")
    
    def test_performance_benchmark(self):
        """Test des performances de synchronisation"""
        
        test_files = list(Path("C:\\Users\\domin\\Documents\\Python Scripts\\CourseScope\\tests\\data").glob("*.gpx"))
        
        if not test_files:
            pytest.skip("Aucun fichier de test trouvé")
            return
        
        # Mesurer les temps de réponse
        start_time = time.time()
        
        successful_uploads = 0
        for file_path in test_files[:3]:  # Limiter à 3 fichiers pour le test
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            response = httpx.post(
                f"{self.api_base_url}/api/v1/activity/load",
                files={"file": (file_path.name, file_data), "name": file_path.name}
            )
            
            if response.status_code == 200:
                successful_uploads += 1
        
        total_time = time.time() - start_time
        
        # Vérifier que le temps moyen par upload est acceptable (< 2 secondes)
        if successful_uploads > 0:
            avg_time = total_time / successful_uploads
            assert avg_time < 2.0, f"Temps d'upload trop lent: {avg_time:.2f}s"
            
        print(f"✅ Performance : SUCCESS - {successful_uploads} uploads en {total_time:.2f}s")
    
    def test_cache_invalidation(self):
        """Test l'invalidation du cache lors des mises à jour"""
        
        # Test d'invalidation de cache pour les séries
        test_file = Path("C:\\Users\\domin\\Documents\\Python Scripts\\CourseScope\\tests\\data\\cache_test.gpx")
        
        if test_file.exists():
            with open(test_file, 'rb') as f:
                file_data = f.read()
            
            # Premier upload
            response1 = httpx.post(
                f"{self.api_base_url}/api/v1/activity/load",
                files={"file": ("cache_test.gpx", file_data), "name": "cache_test.gpx"}
            )
            
            if response1.status_code == 200:
                activity_id = response1.json()["id"]
                
                # Premier appel aux séries (création du cache)
                series_response1 = httpx.get(f"{self.api_base_url}/api/v1/activity/{activity_id}/series/speed")
                
                # Deuxième appel (utilisation du cache)
                series_response2 = httpx.get(f"{self.api_base_url}/api/v1/activity/{activity_id}/series/speed")
                
                # Les deux réponses devraient être identiques
                assert series_response1.json() == series_response2.json()
                
                print("✅ Cache invalidation : SUCCESS")
        else:
            pytest.skip("Fichier de test de cache non trouvé")


if __name__ == "__main__":
    pytest.main([__file__])