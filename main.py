from fastapi import FastAPI, HTTPException, Header, status
from pydantic import BaseModel, Field
from typing import Optional, List
import sqlite3


from database import get_db_connection, init_db

app = FastAPI(
    title="Flash Sale API",
    description="API haute performance pour vente flash avec gestion de stock concurrent.",
    version="1.0.0"
)


@app.on_event("startup")
def startup_event():
    init_db()


class OrderCreate(BaseModel):
    user_id: str = Field(..., example="client_alice", description="ID du client")
    product_id: int = Field(..., example=1, description="ID du produit à acheter")
    quantity: int = Field(1, ge=1, description="Quantité (au moins 1)")
    idempotency_key: Optional[str] = Field(None, example="unique-token-123")    

@app.get("/")
def home():
    return {"message": "Bienvenue sur l'API Flash Sale !", "docs": "/docs"}

@app.get("/products", tags=["Produits"])
def list_products():
    """Lister tous les produits du magasin."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price, stock FROM products")
        return [dict(row) for row in cursor.fetchall()]

@app.get("/products/{product_id}", tags=["Produits"])
def get_product(product_id: int):
    """Voir le stock en temps réel d'un produit."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price, stock FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Produit introuvable")
        return dict(row)    

@app.post("/orders", status_code=status.HTTP_201_CREATED, tags=["Commandes"])
def create_order(
    order: OrderCreate,
    x_idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    Passer une commande :
    1. Vérifie si la requête a déjà été envoyée (idempotence)
    2. Décrémente le stock de façon atomique
    3. Renvoie 409 si stock épuisé
    4. Enregistre la commande
    """
    # La clé d'idempotence peut venir soit du Header HTTP, soit du body JSON
    idempotency_key = x_idempotency_key or order.idempotency_key

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # stepp 1 : Protection contre le double-clic (Idempotence)
        if idempotency_key:
            cursor.execute(
                "SELECT * FROM orders WHERE idempotency_key = ?", 
                (idempotency_key,)
            )
            existing = cursor.fetchone()
            if existing:
                # La commande a déjà été traitée, on la renvoie directement sans retoucher au stock
                return {
                    "message": "Commande déjà traitée (Rejeu idempotent)",
                    "order": dict(existing)
                }

        # stp2 : Vérifier que le produit existe
        cursor.execute("SELECT id FROM products WHERE id = ?", (order.product_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Produit introuvable")

        # steep3 : LA DÉCRÉMENTATION ATOMIQUE (Zéro Overselling)
        # On ne déduit que SI ET SEULEMENT SI le stock actuel est suffisant
        cursor.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
            (order.quantity, order.product_id, order.quantity)
        )

        # cursor.rowcount = nombre de lignes modifiées par le UPDATE
        if cursor.rowcount == 0:
            # 0 ligne modifiée = il n'y avait plus assez de stock !
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Produit épuisé (Sold out) ! Plus de stock disponible."
            )

        # ÉTAPE 4 : Enregistrer la commande
        try:
            cursor.execute(
                "INSERT INTO orders (user_id, product_id, quantity, idempotency_key) VALUES (?, ?, ?, ?)",
                (order.user_id, order.product_id, order.quantity, idempotency_key)
            )
            order_id = cursor.lastrowid
            conn.commit()
        except sqlite3.IntegrityError:
            # Cas rare où 2 requêtes identiques arrivent à la microseconde exacte
            conn.rollback()
            cursor.execute("SELECT * FROM orders WHERE idempotency_key = ?", (idempotency_key,))
            return {"message": "Commande déjà traitée", "order": dict(cursor.fetchone())}

        return {
            "message": "Commande validée avec succès !",
            "order": {
                "id": order_id,
                "user_id": order.user_id,
                "product_id": order.product_id,
                "quantity": order.quantity,
                "idempotency_key": idempotency_key
            }
        }    

@app.get("/orders", tags=["Commandes"])
def list_orders(user_id: Optional[str] = None):
    """Voir l'historique des commandes (filtrable par user_id)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", 
                (user_id,)
            )
        else:
            cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]
#cette route va reinitialiser la bdd genre je l'ai ajouté pour les tests avec le fichier test.py
@app.post("/reset", tags=["Admin"])
def reset_database():
    """
    Réinitialise les stocks et vide les commandes pour pouvoir retester.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
       
        cursor.execute("DELETE FROM orders;")
        
        
        cursor.execute("UPDATE products SET stock = 5 WHERE id = 1;")   # PS5 -> 5
        cursor.execute("UPDATE products SET stock = 10 WHERE id = 2;")  # Sony -> 10
        cursor.execute("UPDATE products SET stock = 3 WHERE id = 3;")   # iPhone -> 3
        
        conn.commit()
        
    return {
        "message": "Base de données réinitialisée avec succès !",
        "stocks": {
            "PlayStation 5 (ID 1)": 5,
            "Casque Sony (ID 2)": 10,
            "iPhone 15 Pro (ID 3)": 3
        }
    }    