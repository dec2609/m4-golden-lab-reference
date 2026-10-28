export type OrderStatus = "pending" | "confirmed" | "shipped" | "cancelled" | string;

export interface Order {
  id: number;
  customer_name: string;
  product_name: string;
  quantity: number;
  status: OrderStatus;
  created_at: string;
}

export interface CreateOrderInput {
  customer_name: string;
  product_name: string;
  quantity: number;
}
