import { useState, type FormEvent } from "react";
import Button from "../ui/Button";
import Input from "../ui/Input";
import type { CreateOrderInput } from "../../types/order";
import { MAX_ORDER_QUANTITY, validOrderQuantity } from "../../config/orders";

export interface CreateOrderFormProps {
  onSubmit: (values: CreateOrderInput) => Promise<void>;
  submitting?: boolean;
  onCancel?: () => void;
}

export default function CreateOrderForm({
  onSubmit,
  submitting = false,
  onCancel,
}: CreateOrderFormProps) {
  const [customerName, setCustomerName] = useState("");
  const [productName, setProductName] = useState("");
  const [quantity, setQuantity] = useState("1");

  const [customerError, setCustomerError] = useState<string | null>(null);
  const [productError, setProductError] = useState<string | null>(null);
  const [quantityError, setQuantityError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setCustomerError(null);
    setProductError(null);
    setQuantityError(null);
    setFormError(null);

    let hasError = false;

    if (!customerName.trim()) {
      setCustomerError("Customer name is required.");
      hasError = true;
    }

    if (!productName.trim()) {
      setProductError("Product name is required.");
      hasError = true;
    }

    const parsedQuantity = Number(quantity);
    if (
      !quantity.trim() ||
      !validOrderQuantity(parsedQuantity)
    ) {
      setQuantityError("Quantity must be an integer between 1 and 2147483647.");
      hasError = true;
    }

    if (hasError) {
      return;
    }

    try {
      await onSubmit({
        customer_name: customerName.trim(),
        product_name: productName.trim(),
        quantity: parsedQuantity,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create order.";
      setFormError(msg);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      <div>
        <label
          htmlFor="customer-name"
          className="mb-1.5 block text-sm font-medium text-[var(--text-primary)]"
        >
          Customer name <span className="text-[var(--danger)]">*</span>
        </label>
        <Input
          id="customer-name"
          value={customerName}
          onChange={(e) => {
            setCustomerName(e.target.value);
            if (customerError) setCustomerError(null);
          }}
          placeholder="e.g. Nguyen Van A"
          disabled={submitting}
          error={Boolean(customerError)}
          aria-invalid={Boolean(customerError)}
          aria-describedby={customerError ? "customer-error" : undefined}
        />
        {customerError && (
          <p id="customer-error" className="mt-1 text-xs text-[var(--danger)]" role="alert">
            {customerError}
          </p>
        )}
      </div>

      <div>
        <label
          htmlFor="product-name"
          className="mb-1.5 block text-sm font-medium text-[var(--text-primary)]"
        >
          Product name <span className="text-[var(--danger)]">*</span>
        </label>
        <Input
          id="product-name"
          value={productName}
          onChange={(e) => {
            setProductName(e.target.value);
            if (productError) setProductError(null);
          }}
          placeholder="e.g. Laptop"
          disabled={submitting}
          error={Boolean(productError)}
          aria-invalid={Boolean(productError)}
          aria-describedby={productError ? "product-error" : undefined}
        />
        {productError && (
          <p id="product-error" className="mt-1 text-xs text-[var(--danger)]" role="alert">
            {productError}
          </p>
        )}
      </div>

      <div>
        <label
          htmlFor="quantity"
          className="mb-1.5 block text-sm font-medium text-[var(--text-primary)]"
        >
          Quantity <span className="text-[var(--danger)]">*</span>
        </label>
        <Input
          id="quantity"
          type="number"
          min={1}
          max={MAX_ORDER_QUANTITY}
          step={1}
          value={quantity}
          onChange={(e) => {
            setQuantity(e.target.value);
            if (quantityError) setQuantityError(null);
          }}
          placeholder="1"
          disabled={submitting}
          error={Boolean(quantityError)}
          aria-invalid={Boolean(quantityError)}
          aria-describedby={quantityError ? "quantity-error" : undefined}
        />
        {quantityError && (
          <p id="quantity-error" className="mt-1 text-xs text-[var(--danger)]" role="alert">
            {quantityError}
          </p>
        )}
      </div>

      {formError && (
        <div className="rounded-[var(--radius-control)] border border-[var(--danger)]/20 bg-[var(--danger-soft)] p-3 text-sm text-[var(--danger)]">
          {formError}
        </div>
      )}

      <div className="flex items-center justify-end gap-3 pt-2 border-t border-[var(--border)]">
        {onCancel && (
          <Button
            type="button"
            variant="secondary"
            onClick={onCancel}
            disabled={submitting}
          >
            Cancel
          </Button>
        )}
        <Button type="submit" loading={submitting}>
          Create Order
        </Button>
      </div>
    </form>
  );
}
