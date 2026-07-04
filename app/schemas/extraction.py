from pydantic import BaseModel, Field

from app.schemas.enums import DocumentType


class InvoiceFields(BaseModel):
  invoice_number: str | None = None
  invoice_date: str | None = None
  vendor_name: str | None = None
  buyer_name: str | None = None
  currency: str | None = None
  subtotal: str | None = None
  tax: str | None = None
  total: str | None = None
  due_date: str | None = None


class ReceiptFields(BaseModel):
  receipt_number: str | None = None
  receipt_date: str | None = None
  merchant_name: str | None = None
  currency: str | None = None
  subtotal: str | None = None
  tax: str | None = None
  total: str | None = None
  payment_method: str | None = None


class PurchaseOrderFields(BaseModel):
  po_number: str | None = None
  po_date: str | None = None
  vendor_name: str | None = None
  buyer_name: str | None = None
  currency: str | None = None
  total: str | None = None
  delivery_date: str | None = None


class ExtractionResult(BaseModel):
  segment_id: str
  document_type: DocumentType
  fields: InvoiceFields | ReceiptFields | PurchaseOrderFields
  raw_text: str = ""
  extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
  provider: str = "heuristic"
