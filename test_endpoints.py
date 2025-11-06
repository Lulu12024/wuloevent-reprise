#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Test Automatisé des 11 Endpoints
Tickets Backend - Super-Vendeurs et Vendeurs

Usage:
    python test_endpoints.py

Requirements:
    pip install requests --break-system-packages
"""

import requests
import json
from typing import Dict, Optional
from datetime import datetime, timedelta

class EndpointTester:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.token_super_vendeur: Optional[str] = None
        self.token_vendeur: Optional[str] = None
        self.org_id: Optional[str] = None
        self.event_id: Optional[str] = None
        self.seller_id: Optional[str] = None
        self.invitation_token: Optional[str] = None
        
    def print_header(self, text: str):
        """Afficher un en-tête formaté"""
        print("\n" + "="*60)
        print(f" {text}")
        print("="*60)
    
    def print_result(self, endpoint: str, status_code: int, response: dict):
        """Afficher le résultat d'un test"""
        status = "✅ SUCCÈS" if 200 <= status_code < 300 else "❌ ÉCHEC"
        print(f"\n{status} - {endpoint}")
        print(f"Status Code: {status_code}")
        print(f"Response: {json.dumps(response, indent=2, ensure_ascii=False)}")
    
    def make_request(self, method: str, endpoint: str, data: dict = None, 
                    token: str = None, files: dict = None) -> tuple:
        """Effectuer une requête HTTP"""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        if files:
            headers.pop("Content-Type", None)
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                if files:
                    response = requests.post(url, headers=headers, data=data, files=files)
                else:
                    response = requests.post(url, headers=headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Méthode HTTP non supportée: {method}")
            
            return response.status_code, response.json() if response.text else {}
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur de requête: {e}")
            return 0, {}
        except json.JSONDecodeError:
            return response.status_code, {"error": "Invalid JSON response"}
    
    # ==================== PRÉREQUIS ====================
    
    def test_0_register_super_vendeur(self):
        """0.1 - Créer un utilisateur Super-Vendeur"""
        self.print_header("0.1 - Inscription Super-Vendeur")
        
        data = {
            "email": "supervendeur@test.com",
            "password": "Pass123!",
            "password_confirm": "Pass123!",
            "first_name": "Jean",
            "last_name": "Dupont",
            "phone": "+22997000001"
        }
        
        status, response = self.make_request("POST", "/api/auth/register/", data)
        self.print_result("Register Super-Vendeur", status, response)
        return status in [200, 201]
    
    def test_0_register_vendeur(self):
        """0.2 - Créer un utilisateur Vendeur"""
        self.print_header("0.2 - Inscription Vendeur")
        
        data = {
            "email": "vendeur@test.com",
            "password": "Pass123!",
            "password_confirm": "Pass123!",
            "first_name": "Marie",
            "last_name": "Martin",
            "phone": "+22997000002"
        }
        
        status, response = self.make_request("POST", "/api/auth/register/", data)
        self.print_result("Register Vendeur", status, response)
        return status in [200, 201]
    
    def test_0_login_super_vendeur(self):
        """0.3 - Connexion Super-Vendeur"""
        self.print_header("0.3 - Login Super-Vendeur")
        
        data = {
            "email": "supervendeur@test.com",
            "password": "Pass123!"
        }
        
        status, response = self.make_request("POST", "/api/auth/login/", data)
        self.print_result("Login Super-Vendeur", status, response)
        
        if status == 200 and "access" in response:
            self.token_super_vendeur = response["access"]
            print(f"\n🔑 Token Super-Vendeur: {self.token_super_vendeur[:50]}...")
            return True
        return False
    
    def test_0_login_vendeur(self):
        """0.4 - Connexion Vendeur"""
        self.print_header("0.4 - Login Vendeur")
        
        data = {
            "email": "vendeur@test.com",
            "password": "Pass123!"
        }
        
        status, response = self.make_request("POST", "/api/auth/login/", data)
        self.print_result("Login Vendeur", status, response)
        
        if status == 200 and "access" in response:
            self.token_vendeur = response["access"]
            print(f"\n🔑 Token Vendeur: {self.token_vendeur[:50]}...")
            return True
        return False
    
    def test_0_create_organization(self):
        """0.5 - Créer une Organisation"""
        self.print_header("0.5 - Création Organisation")
        
        data = {
            "name": "TechSell Organisation",
            "organization_type": "SUPER_SELLER",
            "email": "contact@techsell.com",
            "phone": "+22997111111",
            "address": "123 Avenue de la République",
            "city": "Cotonou",
            "country": "BJ"
        }
        
        status, response = self.make_request(
            "POST", "/api/organizations/", data, self.token_super_vendeur
        )
        self.print_result("Create Organization", status, response)
        
        if status in [200, 201] and "id" in response:
            self.org_id = response["id"]
            print(f"\n🏢 Organisation ID: {self.org_id}")
            return True
        return False
    
    # ==================== TESTS DES 11 ENDPOINTS ====================
    
    def test_1_invite_seller(self):
        """1. Inviter un Vendeur"""
        self.print_header("TEST 1 - Inviter un Vendeur")
        
        data = {
            "organization_id": self.org_id,
            "email": "vendeur@test.com",
            "channel": "EMAIL",
            "message": "Rejoignez notre équipe de vente !"
        }
        
        status, response = self.make_request(
            "POST", "/v1/api/sellers/invite/", data, self.token_super_vendeur
        )
        self.print_result("Invite Seller", status, response)
        
        if status in [200, 201] and "token" in response:
            self.invitation_token = response["token"]
            print(f"\n📧 Invitation Token: {self.invitation_token}")
            return True
        return False
    
    def test_2_respond_invitation(self):
        """2. Répondre à l'Invitation"""
        self.print_header("TEST 2 - Répondre à l'Invitation (ACCEPT)")
        
        data = {
            "action": "ACCEPT"
        }
        
        endpoint = f"/v1/api/sellers/invitations/{self.invitation_token}/respond/"
        status, response = self.make_request(
            "POST", endpoint, data, self.token_vendeur
        )
        self.print_result("Respond to Invitation", status, response)
        
        if status in [200, 201]:
            if "seller" in response and "id" in response["seller"]:
                self.seller_id = response["seller"]["id"]
                print(f"\n👤 Seller ID: {self.seller_id}")
            return True
        return False
    
    def test_3_create_ephemeral_event(self):
        """3. Créer un Événement Éphémère"""
        self.print_header("TEST 3 - Créer un Événement Éphémère")
        
        future_date = (datetime.now() + timedelta(days=50)).strftime("%Y-%m-%d")
        expiry_date = (datetime.now() + timedelta(days=51)).strftime("%Y-%m-%dT23:59:59Z")
        
        data = {
            "name": "Concert Privé VIP",
            "description": "Concert exclusif pour les membres privilégiés",
            "type": 1,
            "organization": self.org_id,
            "default_price": 50000,
            "date": future_date,
            "hour": "20:00:00",
            "expiry_date": expiry_date,
            "location_name": "Centre Culturel de Cotonou",
            "location_lat": 6.3654,
            "location_long": 2.4183,
            "country": 1,
            "participant_limit": 100
        }
        
        status, response = self.make_request(
            "POST", "/v1/api/super-sellers/events/ephemeral/", 
            data, self.token_super_vendeur
        )
        self.print_result("Create Ephemeral Event", status, response)
        
        if status in [200, 201] and "pk" in response:
            self.event_id = response["pk"]
            print(f"\n🎫 Event ID: {self.event_id}")
            print(f"🔒 Access Code: {response.get('ephemeral_access_code', 'N/A')}")
            return True
        return False
    
    def test_4_list_ephemeral_events(self):
        """4. Liste des Événements Éphémères"""
        self.print_header("TEST 4 - Liste des Événements Éphémères")
        
        status, response = self.make_request(
            "GET", "/v1/api/super-sellers/events/ephemeral/", 
            token=self.token_super_vendeur
        )
        self.print_result("List Ephemeral Events", status, response)
        return status == 200
    
    def test_5_get_ephemeral_event_details(self):
        """5. Détails d'un Événement Éphémère"""
        self.print_header("TEST 5 - Détails d'un Événement Éphémère")
        
        endpoint = f"/v1/api/super-sellers/events/ephemeral/{self.event_id}/"
        status, response = self.make_request(
            "GET", endpoint, token=self.token_super_vendeur
        )
        self.print_result("Get Event Details", status, response)
        return status == 200
    
    def test_6_get_event_statistics(self):
        """6. Statistiques d'un Événement"""
        self.print_header("TEST 6 - Statistiques d'un Événement")
        
        endpoint = f"/v1/api/super-sellers/events/ephemeral/{self.event_id}/statistics/"
        status, response = self.make_request(
            "GET", endpoint, token=self.token_super_vendeur
        )
        self.print_result("Get Event Statistics", status, response)
        return status == 200
    
    def test_7_list_sellers(self):
        """7. Liste des Vendeurs"""
        self.print_header("TEST 7 - Liste des Vendeurs")
        
        status, response = self.make_request(
            "GET", "/v1/sellers/", token=self.token_super_vendeur
        )
        self.print_result("List Sellers", status, response)
        return status == 200
    
    def test_8_get_seller_details(self):
        """8. Détails d'un Vendeur"""
        self.print_header("TEST 8 - Détails d'un Vendeur")
        
        endpoint = f"/v1/sellers/{self.seller_id}/"
        status, response = self.make_request(
            "GET", endpoint, token=self.token_super_vendeur
        )
        self.print_result("Get Seller Details", status, response)
        return status == 200
    
    def test_9_delete_seller(self):
        """9. Retirer un Vendeur (à faire en dernier)"""
        self.print_header("TEST 9 - Retirer un Vendeur")
        
        endpoint = f"/v1/sellers/{self.seller_id}/"
        status, response = self.make_request(
            "DELETE", endpoint, token=self.token_super_vendeur
        )
        self.print_result("Delete Seller", status, response)
        return status in [200, 204]
    
    def test_10_sell_tickets(self):
        """10. Vente de Tickets par un Vendeur"""
        self.print_header("TEST 10 - Vente de Tickets")
        
        data = {
            "event": self.event_id,
            "quantity": 2,
            "customer_name": "Kokou ADDO",
            "customer_email": "kokou@example.com",
            "customer_phone": "+22997888888",
            "payment_method": "MOBILE_MONEY",
            "payment_reference": f"MM-{datetime.now().strftime('%Y%m%d')}-001"
        }
        
        status, response = self.make_request(
            "POST", "/v1/sellers/tickets/sell", 
            data, self.token_vendeur
        )
        self.print_result("Sell Tickets", status, response)
        return status in [200, 201]
    
    def test_11_allocate_stock(self):
        """11. Allouer du Stock à un Vendeur"""
        self.print_header("TEST 11 - Allouer du Stock")
        
        data = {
            "event": self.event_id,
            "quantity": 50,
            "notes": "Stock initial pour démarrage"
        }
        
        endpoint = f"/v1/super-sellers/sellers/{self.seller_id}/stock/allocate/"
        status, response = self.make_request(
            "POST", endpoint, data, self.token_super_vendeur
        )
        self.print_result("Allocate Stock", status, response)
        return status in [200, 201]
    
    # ==================== RUNNER ====================
    
    def run_all_tests(self):
        """Exécuter tous les tests dans l'ordre"""
        print("\n🚀 DÉBUT DES TESTS - Backend Tickets")
        print(f"Base URL: {self.base_url}")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        results = {}
        
        # Prérequis
        print("\n" + "="*60)
        print(" PHASE 0: PRÉREQUIS")
        print("="*60)
        
        results["0.1 - Register Super-Vendeur"] = self.test_0_register_super_vendeur()
        results["0.2 - Register Vendeur"] = self.test_0_register_vendeur()
        results["0.3 - Login Super-Vendeur"] = self.test_0_login_super_vendeur()
        results["0.4 - Login Vendeur"] = self.test_0_login_vendeur()
        results["0.5 - Create Organization"] = self.test_0_create_organization()
        
        # Tests des 11 endpoints
        print("\n" + "="*60)
        print(" PHASE 1: TESTS DES 11 ENDPOINTS")
        print("="*60)
        
        # Ordre logique de test
        results["1 - Invite Seller"] = self.test_1_invite_seller()
        results["2 - Respond Invitation"] = self.test_2_respond_invitation()
        results["3 - Create Event"] = self.test_3_create_ephemeral_event()
        results["4 - List Events"] = self.test_4_list_ephemeral_events()
        results["5 - Event Details"] = self.test_5_get_ephemeral_event_details()
        results["11 - Allocate Stock"] = self.test_11_allocate_stock()  # Avant la vente
        results["7 - List Sellers"] = self.test_7_list_sellers()
        results["8 - Seller Details"] = self.test_8_get_seller_details()
        results["10 - Sell Tickets"] = self.test_10_sell_tickets()
        results["6 - Event Statistics"] = self.test_6_get_event_statistics()
        results["9 - Delete Seller"] = self.test_9_delete_seller()
        
        # Résumé
        self.print_header("RÉSUMÉ DES TESTS")
        
        passed = sum(1 for result in results.values() if result)
        failed = len(results) - passed
        
        print(f"\nTotal: {len(results)} tests")
        print(f"✅ Réussis: {passed}")
        print(f"❌ Échoués: {failed}")
        print(f"Taux de réussite: {(passed/len(results)*100):.1f}%")
        
        print("\n" + "-"*60)
        for test_name, result in results.items():
            status = "✅" if result else "❌"
            print(f"{status} {test_name}")
        
        print("\n🏁 FIN DES TESTS\n")

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║   Script de Test - Backend Tickets                    ║
    ║   11 Endpoints Super-Vendeurs et Vendeurs             ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    # Vérifier que le serveur est accessible
    try:
        response = requests.get("http://127.0.0.1:8000")
        print("✅ Serveur accessible\n")
    except requests.exceptions.RequestException:
        print("❌ ERREUR: Serveur non accessible sur http://127.0.0.1:8000")
        print("Assurez-vous que le serveur Django est démarré.\n")
        exit(1)
    
    # Lancer les tests
    tester = EndpointTester()
    tester.run_all_tests()