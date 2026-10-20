import asyncio
import httpx
import uuid
import sys

BASE_URL = "http://127.0.0.1:8000"

# i made this code to test my BEAUUUTIFUUUL api *_*

async def test_flash_sale(client: httpx.AsyncClient, product_id: int, total_clients: int):
    print("\n" + "="*65)
    print(f" TEST 1 : VENTE FLASH ({total_clients} clients différents en même temps)")
    print(f" Produit ciblé : ID {product_id}")
    print("="*65)

    res = await client.get(f"/products/{product_id}")
    if res.status_code == 404:
        print(f" Le produit {product_id} n'existe pas !")
        return False

    prod = res.json()
    initial_stock = prod["stock"]
    print(f" Produit : {prod['name']}")
    print(f" Stock disponible pour la vente flash : {initial_stock} unités\n")

    if initial_stock <= 0:
        print(f" Le produit est déjà épuisé (stock = 0) !")
        return False

    print(f" Envoi de {total_clients} requêtes simultanées...")

    async def buy(i):
        return await client.post(
            "/orders",
            json={
                "user_id": f"client_{i}",
                "product_id": product_id,
                "quantity": 1,
                "idempotency_key": str(uuid.uuid4())
            }
        )

    responses = await asyncio.gather(*[buy(i) for i in range(total_clients)])

    successes = [r for r in responses if r.status_code == 201]
    sold_outs = [r for r in responses if r.status_code == 409]

    print("\n RÉSULTATS DU TEST 1 :")
    print(f"   Commandes acceptées (201)        : {len(successes)}")
    print(f"   Commandes refusées 'Sold Out' (409) : {len(sold_outs)}")

    res_after = await client.get(f"/products/{product_id}")
    final_stock = res_after.json()["stock"]
    print(f" Stock restant après la vente : {final_stock}")

    if final_stock >= 0 and len(successes) <= initial_stock:
        print(" TEST 1 RÉUSSI : Aucun overselling, le stock n'est jamais négatif !")
        return True
    else:
        print(" TEST 1 ÉCHOUÉ : Il y a eu de la survente !")
        return False


async def test_double_click(client: httpx.AsyncClient, product_id: int):
    print("\n" + "="*65)
    print(" TEST 2 : PROTECTION DOUBLE-CLIC / RETRY (IDEMPOTENCE)")
    print(f" Produit ciblé : ID {product_id}")
    print("="*65)

    # Vérificayshen of le stock avant
    res_before = await client.get(f"/products/{product_id}")
    if res_before.status_code == 404:
        print(f" Le produit {product_id} n'existe pas !")
        return False

    stock_before = res_before.json()["stock"]
    if stock_before <= 0:
        print(" Pas assez de stock pour ce test.")
        return False

    user = "alice_impatiente"
    same_idempotency_key = "clic-unique-" + str(uuid.uuid4())

    print(f" Utilisateur '{user}' clique 5 FOIS d'affilée à la même milliseconde...")
    print(f" Clé envoyée : {same_idempotency_key}\n")

    async def spam_order():
        return await client.post(
            "/orders",
            json={
                "user_id": user,
                "product_id": product_id,
                "quantity": 1,
                "idempotency_key": same_idempotency_key
            }
        )

    # 5 clics envoyés en même temps avec la même clé::::
    responses = await asyncio.gather(*[spam_order() for _ in range(5)])

    print("📬 Réponses reçues pour les 5 clics :")
    for i, r in enumerate(responses, 1):
        msg = r.json().get("message", "Pas de message")
        print(f"  Clic {i} : Code HTTP {r.status_code} -> \"{msg}\"")

    # Vérificayshen :
    # 1. Combien de commandes sont enregistrées en BDD pour Alice ?
    orders_res = await client.get(f"/orders?user_id={user}")
    alice_orders = orders_res.json()
    total_orders = len(alice_orders)

    # 2. De combien le stock a-t-il baissé ?
    res_after = await client.get(f"/products/{product_id}")
    stock_after = res_after.json()["stock"]

    print(f"\n Bilan pour {user} :")
    print(f"  - Commandes réellement créées en BDD : {total_orders} (Attendu: 1)")
    print(f"  - Stock avant: {stock_before} | Stock après: {stock_after} (Diminution de: {stock_before - stock_after})")

    if total_orders == 1 and (stock_before - stock_after == 1):
        print("\n TEST 2 marche yeyyy")
        return True
    else:
        print("\n TEST 2  marcheeeeee paaaaas")
        return False


async def main():
    # Récupérer l'ID en argument de commande ou demander
    if len(sys.argv) > 1:
        try:
            prod_id = int(sys.argv[1])
        except ValueError:
            print("L'ID doit être un nombre !")
            return
    else:
        user_input = input("Entrez l'ID du produit à tester (ex: 1, 2, 3) [Défaut: 1] : ").strip()
        prod_id = int(user_input) if user_input else 1

    clients_count = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        try:
            # 1 Remet les stocks à neuf pour que le produit choisi soit plein
            await client.post("/reset")

            # 2 Test 2 sur le produit choisi (prod_id)
            await test_double_click(client, prod_id)
            
            # 3 Test 1 sur le produit choisi (prod_id)
            await test_flash_sale(client, prod_id, clients_count)

            print("\n" + "="*65)
            print("ça marchheeeee youpiii")
            print("="*65 + "\n")
        except httpx.ConnectError:
            print("\nça marche paaaas!! Assure-toi que uvicorn tourne !")


if __name__ == "__main__":
    asyncio.run(main())