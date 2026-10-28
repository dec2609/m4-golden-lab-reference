/** Order quantity boundary matching PostgreSQL INTEGER and the PR #14 contract. */
export const MAX_ORDER_QUANTITY = 2_147_483_647;
export const validOrderQuantity = (value: unknown): value is number =>
  typeof value === "number" && Number.isSafeInteger(value) && value >= 1 && value <= MAX_ORDER_QUANTITY;
