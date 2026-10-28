import type { Order } from "../types/order";

/**
 * UI fixtures only.
 * This data is NOT technical evidence.
 */
export const initialMockOrders: Order[] = [
  {
    id: 1001,
    customer_name: "Nguyen Van An",
    product_name: "Laptop",
    quantity: 2,
    status: "pending",
    created_at: "2026-10-07T01:15:00Z",
  },
  {
    id: 1002,
    customer_name: "Tran Minh Chau",
    product_name: "Monitor",
    quantity: 1,
    status: "pending",
    created_at: "2026-10-07T00:42:00Z",
  },
  {
    id: 1003,
    customer_name: "Le Hoang Nam",
    product_name: "Keyboard",
    quantity: 3,
    status: "pending",
    created_at: "2026-10-06T15:28:00Z",
  },
  {
    id: 1004,
    customer_name: "Pham Gia Han",
    product_name: "Laptop Stand",
    quantity: 2,
    status: "pending",
    created_at: "2026-10-06T13:10:00Z",
  },
  {
    id: 1005,
    customer_name: "Vo Minh Khang",
    product_name: "Webcam",
    quantity: 1,
    status: "pending",
    created_at: "2026-10-06T09:35:00Z",
  },
  {
    id: 1006,
    customer_name: "Nguyen Thu Ha",
    product_name: "USB-C Hub",
    quantity: 4,
    status: "pending",
    created_at: "2026-10-05T16:22:00Z",
  },
  {
    id: 1007,
    customer_name: "Do Thanh Tung",
    product_name: "Mechanical Keyboard",
    quantity: 1,
    status: "pending",
    created_at: "2026-10-05T11:48:00Z",
  },
  {
    id: 1008,
    customer_name: "Bui Khanh Linh",
    product_name: "External SSD",
    quantity: 2,
    status: "pending",
    created_at: "2026-10-04T08:16:00Z",
  },
];

// Each adapter owns its demo store; fixtures never stand in for persisted data.
export function createMockOrdersStore() {
  let currentOrders: Order[] = initialMockOrders.map((order) => ({ ...order }));
  let nextOrderId = 1009;

  function getMockOrders(): Order[] {
    return currentOrders.map((order) => ({ ...order }));
  }

  function resetMockOrders(): void {
    currentOrders = initialMockOrders.map((order) => ({ ...order }));
    nextOrderId = 1009;
  }

  function clearMockOrders(): void {
    currentOrders = [];
  }

  function addMockOrder(orderData: {
    customer_name: string;
    product_name: string;
    quantity: number;
  }): Order {
    const newOrder: Order = {
      id: nextOrderId++,
      customer_name: orderData.customer_name,
      product_name: orderData.product_name,
      quantity: orderData.quantity,
      status: "pending",
      created_at: new Date().toISOString(),
    };

    currentOrders = [newOrder, ...currentOrders];
    return { ...newOrder };
  }

  return { getMockOrders, resetMockOrders, clearMockOrders, addMockOrder };
}
