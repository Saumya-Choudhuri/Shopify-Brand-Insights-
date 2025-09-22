from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any

class Product(BaseModel):
    id: Optional[int] = None
    title: Optional[str] = None
    handle: Optional[str] = None
    price: Optional[str] = None
    url: Optional[HttpUrl] = None
    image: Optional[str] = None

class FAQPair(BaseModel):
    q: str
    a: str

class FAQs(BaseModel):
    url: Optional[HttpUrl] = None
    qa_pairs: Optional[List[FAQPair]] = None

class StoreHeader(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    meta_description: Optional[str] = None

class Contacts(BaseModel):
    emails: Optional[List[str]] = None
    phones: Optional[List[str]] = None
    contact_page: Optional[HttpUrl] = None

class BrandAbout(BaseModel):
    about_url: Optional[HttpUrl] = None
    about_excerpt: Optional[str] = None

class BrandContext(BaseModel):
    store: StoreHeader
    whole_product_catalog: Optional[List[Product]] = None
    hero_products: Optional[List[Product]] = None
    privacy_policy_url: Optional[HttpUrl] = None
    privacy_policy_excerpt: Optional[str] = None
    refund_policy_url: Optional[HttpUrl] = None
    refund_policy_excerpt: Optional[str] = None
    return_policy_url: Optional[HttpUrl] = None
    return_policy_excerpt: Optional[str] = None
    brand_faqs: FAQs
    social_handles: Optional[Dict[str, str]] = None
    contacts: Contacts
    brand_context: BrandAbout
    important_links: Optional[Dict[str, str]] = None

class BrandContextRequest(BaseModel):
    website_url: str = Field(..., description="Full https URL or domain")