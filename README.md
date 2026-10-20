# ⚡ Flash Sale API
This is a GDG challenge(GIP dev dep)
A high-performance REST API built with **Python (FastAPI)** and **SQLite (WAL mode)** designed for flash sales with limited inventory, high concurrency, zero overselling, and retry/idempotency protection.

---

## 🚀 Key Features & Solutions

### 1. Zero Overselling & High Concurrency
- **SQLite in WAL (Write-Ahead Logging) Mode**: Configured with `PRAGMA journal_mode = WAL;` and `busy_timeout` to support high-throughput concurrent reads and writes without blocking.
- **Atomic Conditional Decrement**: Stock deduction is handled in a single atomic SQL operation:
  ```sql
  UPDATE products 
  SET stock = stock - :quantity 
  WHERE id = :product_id AND stock >= :quantity;