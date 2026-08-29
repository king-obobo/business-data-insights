import pandas as pd
from .db import get_cursor


class SalesRepository:
    """Repository class encapsulating PostgreSQL analytical queries for Apple Retail Sales."""

    def get_top_products_per_store(
        self, rank_limit: int = 3
    ) -> pd.DataFrame:
        """
        Uses a Window Function (DENSE_RANK) to find the top N revenue-generating 
        products for each retail store.
        """
        query = """
        WITH ranked_store_products AS (
            SELECT 
                st.store_id,
                st.store_name,
                st.city,
                p.product_id,
                p.product_name,
                SUM(s.quantity * p.price) AS total_revenue,
                SUM(s.quantity) AS total_units_sold,
                DENSE_RANK() OVER (
                    PARTITION BY st.store_id 
                    ORDER BY SUM(s.quantity * p.price) DESC
                ) AS store_rank
            FROM sales s
            JOIN stores st ON s.store_id = st.store_id
            JOIN products p ON s.product_id = p.product_id
            GROUP BY st.store_id, st.store_name, st.city, p.product_id, p.product_name
        )
        SELECT 
            store_id,
            store_name,
            city,
            product_id,
            product_name,
            total_revenue,
            total_units_sold,
            store_rank
        FROM ranked_store_products
        WHERE store_rank <= %s
        ORDER BY store_id, store_rank;
        """

        with get_cursor() as cur:
            cur.execute(query, (rank_limit,))
            records = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

        return pd.DataFrame(records, columns=columns)

    def get_claim_rate_by_category(self) -> pd.DataFrame:
        """
        Uses CTEs joining Sales, Products, Category, and Warranty tables 
        to compute warranty claim rate (%) across product categories.
        """
        query = """
        WITH sales_by_category AS (
            SELECT 
                c.category_id,
                c.category_name,
                COUNT(s.sale_id) AS total_sales_count,
                SUM(s.quantity) AS total_units_sold
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            JOIN category c ON p.category_id = c.category_id
            GROUP BY c.category_id, c.category_name
        ),
        claims_by_category AS (
            SELECT 
                c.category_id,
                COUNT(w.claim_id) AS total_claims_count
            FROM warranty w
            JOIN sales s ON w.sale_id = s.sale_id
            JOIN products p ON s.product_id = p.product_id
            JOIN category c ON p.category_id = c.category_id
            GROUP BY c.category_id
        )
        SELECT 
            sc.category_id,
            sc.category_name,
            sc.total_sales_count,
            COALESCE(cc.total_claims_count, 0) AS total_claims_count,
            ROUND(
                (COALESCE(cc.total_claims_count, 0)::NUMERIC / NULLIF(sc.total_sales_count, 0)) * 100, 2
            ) AS claim_rate_percentage
        FROM sales_by_category sc
        LEFT JOIN claims_by_category cc ON sc.category_id = cc.category_id
        ORDER BY claim_rate_percentage DESC;
        """

        with get_cursor() as cur:
            cur.execute(query)
            records = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

        return pd.DataFrame(records, columns=columns)
    
    
# def main() -> None:
#     # Instantiate Repository
#     repo = SalesRepository()

#     # 1. Top 3 Products per Store (Window Function)
#     print("\n================ TOP 3 PRODUCTS PER STORE BY REVENUE ================")
#     top_products_df = repo.get_top_products_per_store(rank_limit=3)
#     print(top_products_df.head(3))

#     # 2. Warranty Claim Rate by Category (CTE Join)
#     print("\n============== WARRANTY CLAIM RATE BY CATEGORY ==============")
#     claim_rate_df = repo.get_claim_rate_by_category()
#     print(claim_rate_df)


# if __name__ == "__main__":
#     main()