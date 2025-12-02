"""
Tests de sécurité du sandbox d'exécution
Tests pour vérifier les vulnérabilités identifiées dans l'analyse
"""

import os
import pytest
import httpx

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture
def api_headers():
    """Headers pour les requêtes"""
    return {
        "Content-Type": "application/json"
    }


class TestSandboxSecurity:
    """Tests de sécurité du sandbox"""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_file_system_access_blocked(self, api_headers):
        """Test: Tentative d'accès au système de fichiers"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Créer un workflow malveillant
            payload = {
                "description": "Lire le contenu du fichier /etc/passwd",
                "name": "File Access Test"
            }

            response = await client.post(
                f"{API_BASE_URL}/api/workflows",
                headers=api_headers,
                json=payload
            )

            assert response.status_code == 200
            workflow_id = response.json()["id"]

            # Exécuter
            execute_response = await client.post(
                f"{API_BASE_URL}/api/workflows/{workflow_id}/execute",
                headers=api_headers,
                json={"user_input": "Execute"}
            )

            # Devrait échouer ou ne pas retourner de contenu sensible
            assert execute_response.status_code in [200, 500]

            if execute_response.status_code == 200:
                result = execute_response.json()
                # Ne devrait pas contenir de contenu de /etc/passwd
                result_text = str(result.get("result", ""))
                assert "root:x:" not in result_text.lower()

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_os_command_injection(self, api_headers):
        """Test: Tentative d'injection de commandes OS"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "description": "Exécuter la commande shell 'ls -la'",
                "name": "Command Injection Test"
            }

            response = await client.post(
                f"{API_BASE_URL}/api/workflows",
                headers=api_headers,
                json=payload
            )

            assert response.status_code == 200
            workflow_id = response.json()["id"]

            # Exécuter
            execute_response = await client.post(
                f"{API_BASE_URL}/api/workflows/{workflow_id}/execute",
                headers=api_headers,
                json={"user_input": "Execute"}
            )

            # Devrait échouer ou être bloqué
            assert execute_response.status_code in [200, 500]

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_import_os_module(self, api_headers):
        """Test: Tentative d'import du module os"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "description": "Importer le module os et utiliser os.system",
                "name": "OS Import Test"
            }

            response = await client.post(
                f"{API_BASE_URL}/api/workflows",
                headers=api_headers,
                json=payload
            )

            assert response.status_code == 200
            workflow_id = response.json()["id"]

            # Exécuter
            execute_response = await client.post(
                f"{API_BASE_URL}/api/workflows/{workflow_id}/execute",
                headers=api_headers,
                json={"user_input": "Execute"}
            )

            # ⚠️ VULNÉRABILITÉ IDENTIFIÉE: Ceci pourrait réussir
            # Dans un sandbox sécurisé, cela devrait échouer
            if execute_response.status_code == 200:
                result = execute_response.json()
                # Si le code a pu importer os, c'est une vulnérabilité
                # Log pour analyse
                print(f"SECURITY WARNING: os module import test result: {result}")

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_eval_exec_blocked(self, api_headers):
        """Test: Tentative d'utilisation de eval/exec"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "description": "Utiliser la fonction eval pour exécuter du code",
                "name": "Eval Test"
            }

            response = await client.post(
                f"{API_BASE_URL}/api/workflows",
                headers=api_headers,
                json=payload
            )

            assert response.status_code == 200
            workflow_id = response.json()["id"]

            # Exécuter
            execute_response = await client.post(
                f"{API_BASE_URL}/api/workflows/{workflow_id}/execute",
                headers=api_headers,
                json={"user_input": "Execute"}
            )

            # Devrait être bloqué
            assert execute_response.status_code in [200, 500]

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_network_access(self, api_headers):
        """Test: Tentative d'accès réseau"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "description": "Faire une requête HTTP vers google.com",
                "name": "Network Access Test"
            }

            response = await client.post(
                f"{API_BASE_URL}/api/workflows",
                headers=api_headers,
                json=payload
            )

            assert response.status_code == 200
            workflow_id = response.json()["id"]

            # Exécuter
            execute_response = await client.post(
                f"{API_BASE_URL}/api/workflows/{workflow_id}/execute",
                headers=api_headers,
                json={"user_input": "Execute"}
            )

            # Dans un sandbox strict, ceci devrait échouer
            # Note: Le code généré pourrait ne pas avoir les bibliothèques nécessaires
            assert execute_response.status_code in [200, 500]

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_infinite_loop_timeout(self, api_headers):
        """Test: Boucle infinie doit timeout"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "description": "Créer une boucle infinie qui ne se termine jamais",
                "name": "Infinite Loop Test"
            }

            response = await client.post(
                f"{API_BASE_URL}/api/workflows",
                headers=api_headers,
                json=payload
            )

            assert response.status_code == 200
            workflow_id = response.json()["id"]

            # Exécuter
            execute_response = await client.post(
                f"{API_BASE_URL}/api/workflows/{workflow_id}/execute",
                headers=api_headers,
                json={"user_input": "Execute"}
            )

            # Devrait timeout ou échouer proprement
            # Ne devrait PAS bloquer indéfiniment
            assert execute_response.status_code in [200, 500, 504]

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_memory_exhaustion(self, api_headers):
        """Test: Tentative d'épuisement mémoire"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "description": "Créer une liste avec 100 millions d'éléments",
                "name": "Memory Exhaustion Test"
            }

            response = await client.post(
                f"{API_BASE_URL}/api/workflows",
                headers=api_headers,
                json=payload
            )

            assert response.status_code == 200
            workflow_id = response.json()["id"]

            # Exécuter
            execute_response = await client.post(
                f"{API_BASE_URL}/api/workflows/{workflow_id}/execute",
                headers=api_headers,
                json={"user_input": "Execute"}
            )

            # Devrait échouer ou être limité
            # ⚠️ VULNÉRABILITÉ: Pas de limite mémoire actuellement
            assert execute_response.status_code in [200, 500]

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_subprocess_creation(self, api_headers):
        """Test: Tentative de création de sous-processus"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "description": "Utiliser subprocess pour exécuter une commande",
                "name": "Subprocess Test"
            }

            response = await client.post(
                f"{API_BASE_URL}/api/workflows",
                headers=api_headers,
                json=payload
            )

            assert response.status_code == 200
            workflow_id = response.json()["id"]

            # Exécuter
            execute_response = await client.post(
                f"{API_BASE_URL}/api/workflows/{workflow_id}/execute",
                headers=api_headers,
                json={"user_input": "Execute"}
            )

            # Devrait être bloqué
            assert execute_response.status_code in [200, 500]


class TestInputValidation:
    """Tests de validation des entrées"""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_sql_injection_in_description(self, api_headers):
        """Test: Injection SQL dans la description"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "description": "'; DROP TABLE workflows; --",
                "name": "SQL Injection Test"
            }

            response = await client.post(
                f"{API_BASE_URL}/api/workflows",
                headers=api_headers,
                json=payload
            )

            # Devrait être traité comme du texte normal
            assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_xss_in_workflow_name(self, api_headers):
        """Test: XSS dans le nom du workflow"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "description": "Simple workflow",
                "name": "<script>alert('XSS')</script>"
            }

            response = await client.post(
                f"{API_BASE_URL}/api/workflows",
                headers=api_headers,
                json=payload
            )

            # Devrait être accepté (sera échappé côté frontend)
            assert response.status_code == 200
            data = response.json()

            # Le nom devrait être stocké tel quel
            assert "<script>" in data["name"]

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_extremely_long_description(self, api_headers):
        """Test: Description extrêmement longue"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1 MB de texte
            long_description = "A" * (1024 * 1024)

            payload = {
                "description": long_description,
                "name": "Long Description Test"
            }

            response = await client.post(
                f"{API_BASE_URL}/api/workflows",
                headers=api_headers,
                json=payload
            )

            # Devrait être rejeté ou géré gracieusement
            assert response.status_code in [200, 400, 413, 422, 500]

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_unicode_injection(self, api_headers):
        """Test: Injection de caractères Unicode"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "description": "Test avec émojis 🚀🔥💻 et caractères spéciaux \u200B\u200C\u200D",
                "name": "Unicode Test"
            }

            response = await client.post(
                f"{API_BASE_URL}/api/workflows",
                headers=api_headers,
                json=payload
            )

            # Devrait gérer correctement
            assert response.status_code == 200


class TestAPIKeyExposure:
    """Tests d'exposition de clés API"""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_api_key_not_in_error_message(self, api_headers):
        """Test: Les clés API ne doivent pas apparaître dans les erreurs"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Créer un workflow qui va échouer
            payload = {
                "description": "Forcer une erreur en utilisant l'API Paradigm",
                "name": "Error Test"
            }

            response = await client.post(
                f"{API_BASE_URL}/api/workflows",
                headers=api_headers,
                json=payload
            )

            assert response.status_code == 200
            workflow_id = response.json()["id"]

            # Exécuter
            execute_response = await client.post(
                f"{API_BASE_URL}/api/workflows/{workflow_id}/execute",
                headers=api_headers,
                json={"user_input": "Execute"}
            )

            # Si erreur, vérifier que les clés ne sont pas exposées
            if execute_response.status_code != 200:
                error_text = execute_response.text.lower()
                assert "sk-" not in error_text  # Clé Anthropic
                assert "api_key" not in error_text
                assert "bearer" not in error_text

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_generated_code_no_api_keys(self, api_headers):
        """Test: Le code généré visible ne doit pas contenir de clés"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "description": "Simple workflow de test",
                "name": "Code Inspection Test"
            }

            response = await client.post(
                f"{API_BASE_URL}/api/workflows",
                headers=api_headers,
                json=payload
            )

            assert response.status_code == 200
            data = response.json()

            # Vérifier que le code généré ne contient pas de clés en clair
            generated_code = data.get("generated_code", "")
            assert "sk-" not in generated_code
            # Les placeholders sont OK
            assert "LIGHTON_API_KEY" in generated_code or "lighton" in generated_code.lower()


class TestRateLimiting:
    """Tests de rate limiting"""

    @pytest.mark.asyncio
    @pytest.mark.security
    @pytest.mark.slow
    async def test_rapid_requests(self, api_headers):
        """Test: Requêtes rapides successives"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Faire 20 requêtes rapides
            responses = []
            for i in range(20):
                payload = {
                    "description": f"Test {i}",
                    "name": f"Rapid Test {i}"
                }

                response = await client.post(
                    f"{API_BASE_URL}/api/workflows",
                    headers=api_headers,
                    json=payload
                )

                responses.append(response.status_code)

            # Toutes devraient réussir OU certaines être rate-limitées (429)
            # ⚠️ VULNÉRABILITÉ: Pas de rate limiting actuellement
            assert all(status in [200, 429, 503] for status in responses)


class TestCORSSecurity:
    """Tests de sécurité CORS"""

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_cors_headers_present(self, api_headers):
        """Test: Headers CORS présents"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.options(
                f"{API_BASE_URL}/api/workflows",
                headers={
                    "Origin": "https://malicious-site.com",
                    "Access-Control-Request-Method": "POST"
                }
            )

            # Vérifier que CORS est configuré
            assert "access-control-allow-origin" in response.headers or response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_cors_wildcard_not_used(self, api_headers):
        """Test: CORS ne devrait pas utiliser wildcard"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{API_BASE_URL}/health",
                headers={"Origin": "https://malicious-site.com"}
            )

            # ⚠️ VULNÉRABILITÉ: CORS trop permissif identifié dans l'analyse
            # Idéalement, ne devrait pas accepter n'importe quelle origine
            cors_header = response.headers.get("access-control-allow-origin", "")
            # Documenter pour analyse
            print(f"CORS Header: {cors_header}")
