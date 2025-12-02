"""
Script to upgrade Qdrant database with documents from the official Public Procurement Portal.
This script scrapes documents from https://www.ujn.gov.rs/propisi/ and uploads them to Qdrant.
"""

import os
import uuid
from typing import List, Dict
from urllib.parse import urljoin, urlparse
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv, find_dotenv
from langfuse.openai import openai
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, Distance, VectorParams
from loguru import logger

from config import load_config
from database.utils import embed_text
from constants import KOMPLETNO_PRAVO_COLLECTION

load_dotenv(find_dotenv())

# Base URL for the official portal
BASE_URL = "https://www.ujn.gov.rs/propisi/"


def initialize_qdrant() -> QdrantClient:
    """Initialize Qdrant client."""
    try:
        client = QdrantClient(
            url=os.environ["QDRANT_CLUSTER_URL"],
            api_key=os.environ["QDRANT_API_KEY"]
        )
        logger.info("Qdrant client initialized successfully")
        return client
    except KeyError as e:
        raise EnvironmentError(f"Missing environment variable: {str(e)}")


def ensure_collection_exists(client: QdrantClient, collection_name: str, vector_size: int = 1536):
    """Ensure the collection exists, create if it doesn't."""
    if not client.collection_exists(collection_name=collection_name):
        logger.info(f"Creating collection: {collection_name}")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )
        logger.info(f"Collection {collection_name} created")
    else:
        logger.info(f"Collection {collection_name} already exists")


def scrape_document_links(base_url: str) -> List[Dict[str, str]]:
    """Scrape all document links from the regulations page."""
    documents = []
    
    try:
        response = requests.get(base_url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # First, find all list items (li) which typically contain document links
        list_items = soup.find_all('li')
        for li in list_items:
            link = li.find('a', href=True)
            if link:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if href and text and len(text) > 5:
                    # Skip navigation links
                    if any(nav in text.lower() for nav in ['о нама', 'o nama', 'активности', 'aktivnosti', 'контакт', 'kontakt', 'претрага', 'pretraga']):
                        continue
                    
                    full_url = urljoin(base_url, href)
                    
                    # Determine section type from parent context
                    section_type = None
                    parent = li.find_parent(['ul', 'ol', 'div', 'section'])
                    if parent:
                        parent_text = parent.get_text().lower()
                        # Check for section indicators in parent or previous siblings
                        prev_elements = li.find_all_previous(['h1', 'h2', 'h3', 'h4', 'strong', 'b'], limit=5)
                        for elem in prev_elements:
                            elem_text = elem.get_text().lower()
                            if 'влада' in elem_text or 'vlada' in elem_text or 'републике србије' in elem_text:
                                section_type = 'vlada'
                                break
                            elif 'канцеларија' in elem_text or 'kancelarija' in elem_text:
                                section_type = 'kancelarija'
                                break
                            elif 'министар' in elem_text or 'ministar' in elem_text or 'финансија' in elem_text or 'finansija' in elem_text:
                                section_type = 'ministar_finansija'
                                break
                            elif 'закон' in elem_text or 'zakon' in elem_text:
                                section_type = 'zakon'
                                break
                    
                    if not section_type:
                        section_type = determine_document_type(text, None)
                    
                    if not any(doc['url'] == full_url for doc in documents):
                        documents.append({
                            'title': text,
                            'url': full_url,
                            'type': section_type
                        })
        
        # Find all headings that indicate sections (h2, h3, h4)
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])
        current_section_type = None
        
        for heading in headings:
            heading_text = heading.get_text(strip=True).lower()
            
            # Determine section type from heading
            if 'влада' in heading_text or 'vlada' in heading_text:
                current_section_type = 'vlada'
            elif 'канцеларија' in heading_text or 'kancelarija' in heading_text:
                current_section_type = 'kancelarija'
            elif 'министар' in heading_text or 'ministar' in heading_text or 'финансија' in heading_text or 'finansija' in heading_text:
                current_section_type = 'ministar_finansija'
            elif 'закон' in heading_text or 'zakon' in heading_text:
                current_section_type = 'zakon'
            
            # Find all links after this heading until next heading
            next_heading = heading.find_next_sibling(['h1', 'h2', 'h3', 'h4'])
            if next_heading:
                section_content = heading.find_next_siblings(limit=100)
                section_content = [elem for elem in section_content if elem != next_heading and elem.name not in ['h1', 'h2', 'h3', 'h4']]
            else:
                section_content = heading.find_all_next(limit=100)
            
            # Extract links from this section
            for elem in section_content:
                if elem.name in ['h1', 'h2', 'h3', 'h4']:
                    break
                links = elem.find_all('a', href=True) if hasattr(elem, 'find_all') else []
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    if href and text and len(text) > 5:
                        full_url = urljoin(base_url, href)
                        if not any(doc['url'] == full_url for doc in documents):
                            doc_type = current_section_type or determine_document_type(text, None)
                            documents.append({
                                'title': text,
                                'url': full_url,
                                'type': doc_type
                            })
        
        # Find all links in lists (these are usually the actual document links)
        lists = soup.find_all(['ul', 'ol'])
        for list_elem in lists:
            # Try to determine section from parent, previous heading, or nearby text
            parent = list_elem.find_parent()
            section_type = None
            
            # Check parent text
            if parent:
                parent_text = parent.get_text().lower()
                if 'влада' in parent_text or 'vlada' in parent_text or 'републике србије' in parent_text:
                    section_type = 'vlada'
                elif 'канцеларија' in parent_text or 'kancelarija' in parent_text or 'јавне набавке' in parent_text:
                    section_type = 'kancelarija'
                elif 'министар' in parent_text or 'ministar' in parent_text or 'финансија' in parent_text or 'finansija' in parent_text:
                    section_type = 'ministar_finansija'
            
            # Check previous heading
            prev_heading = list_elem.find_previous(['h1', 'h2', 'h3', 'h4', 'h5'])
            if prev_heading and not section_type:
                heading_text = prev_heading.get_text().lower()
                if 'влада' in heading_text or 'vlada' in heading_text:
                    section_type = 'vlada'
                elif 'канцеларија' in heading_text or 'kancelarija' in heading_text:
                    section_type = 'kancelarija'
                elif 'министар' in heading_text or 'ministar' in heading_text:
                    section_type = 'ministar_finansija'
            
            links = list_elem.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Skip if it's clearly navigation
                if not text or len(text) < 5:
                    continue
                
                text_lower = text.lower()
                if any(nav in text_lower for nav in ['о нама', 'o nama', 'активности', 'aktivnosti', 'контакт', 'kontakt']):
                    continue
                
                # Look for document indicators
                is_document = (
                    any(keyword in text_lower for keyword in [
                        'pravilnik', 'uredba', 'odluka', 'uputstvo', 
                        'izmena', 'dopuna', 'zakon', 'izmenama', 'dopunama'
                    ])
                    or 'službeni glasnik' in text_lower
                    or 'sluzbeni glasnik' in text_lower
                    or href.lower().endswith(('.pdf', '.doc', '.docx'))
                )
                
                if is_document and href:
                    full_url = urljoin(base_url, href)
                    if not any(doc['url'] == full_url for doc in documents):
                        doc_type = section_type or determine_document_type(text, None)
                        documents.append({
                            'title': text,
                            'url': full_url,
                            'type': doc_type
                        })
        
        logger.info(f"Found {len(documents)} document links")
        return documents
        
    except Exception as e:
        logger.error(f"Error scraping document links: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def determine_document_type(text: str, section) -> str:
    """Determine the type of document based on title and section."""
    text_lower = text.lower()
    
    if 'vlada' in text_lower or (section and 'vlada' in str(section).lower()):
        return 'vlada'
    elif 'kancelarija' in text_lower or (section and 'kancelarija' in str(section).lower()):
        return 'kancelarija'
    elif 'ministar' in text_lower or 'finansija' in text_lower or (section and 'ministar' in str(section).lower()):
        return 'ministar_finansija'
    elif 'zakon' in text_lower:
        return 'zakon'
    else:
        return 'other'


def extract_text_from_pdf(url: str) -> str:
    """Extract text from PDF - placeholder for PDF processing."""
    # Note: This would require PyPDF2 or pdfplumber
    # For now, return metadata
    logger.warning(f"PDF extraction not implemented for {url}")
    return f"[PDF Document: {url}]"


def scrape_document_content(url: str) -> Dict[str, str]:
    """Scrape the content of a single document page."""
    try:
        # Check if it's a PDF - try to extract text
        if url.lower().endswith('.pdf'):
            logger.info(f"Attempting to process PDF: {url}")
            # For PDFs, we'll store the URL and title for now
            # In production, you'd use PyPDF2 or pdfplumber to extract text
            filename = url.split('/')[-1]
            return {
                'title': filename.replace('.pdf', '').replace('_', ' ').replace('-', ' '),
                'content': f'[PDF Document: {url}]\n\nNote: PDF text extraction requires additional libraries (PyPDF2/pdfplumber).',
                'url': url
            }
        
        # Check if it's other binary file types
        if url.lower().endswith(('.doc', '.docx', '.xls', '.xlsx')):
            logger.warning(f"Skipping binary file (requires special processing): {url}")
            return {
                'title': url.split('/')[-1],
                'content': f'[Binary file: {url} - requires special processing]',
                'url': url
            }
        
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('Content-Type', '').lower()
        if 'pdf' in content_type or 'application/pdf' in content_type:
            logger.warning(f"Skipping PDF: {url}")
            return {
                'title': url.split('/')[-1],
                'content': f'[PDF file: {url}]',
                'url': url
            }
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract main content - adjust selectors based on actual page structure
        title = soup.find('h1') or soup.find('h2') or soup.find('title')
        title_text = title.get_text(strip=True) if title else url.split('/')[-1]
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Try to find main content area
        content_areas = soup.find_all(['article', 'main', 'div'], class_=lambda x: x and (
            'content' in str(x).lower() or 
            'text' in str(x).lower() or
            'post' in str(x).lower() or
            'entry' in str(x).lower()
        ))
        
        if not content_areas:
            # Fallback: get all paragraph text
            content_areas = soup.find_all('p')
        
        content_text = ""
        for area in content_areas:
            text = area.get_text(separator='\n', strip=True)
            if len(text) > 50:  # Only include substantial content
                content_text += text + "\n\n"
        
        if not content_text or len(content_text) < 100:
            # Last resort: get body text but filter out navigation
            body = soup.find('body')
            if body:
                # Remove navigation and footer elements
                for elem in body.find_all(['nav', 'footer', 'header', 'aside']):
                    elem.decompose()
                content_text = body.get_text(separator='\n', strip=True)
        
        # Clean up content
        content_text = '\n'.join(line.strip() for line in content_text.split('\n') if line.strip())
        
        return {
            'title': title_text,
            'content': content_text,
            'url': url
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {url}: {e}")
        return {
            'title': url.split('/')[-1],
            'content': '',
            'url': url
        }
    except Exception as e:
        logger.error(f"Error scraping document from {url}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'title': 'Error',
            'content': '',
            'url': url
        }


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into chunks with overlap."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap  # Overlap for context
        
    return chunks


def process_and_upload_documents(
    client: QdrantClient,
    documents: List[Dict[str, str]],
    config,
    collection_name: str = KOMPLETNO_PRAVO_COLLECTION
):
    """Process documents and upload to Qdrant."""
    ensure_collection_exists(client, collection_name, vector_size=1536)
    
    total_uploaded = 0
    
    for doc in documents:
        logger.info(f"Processing: {doc['title']}")
        
        # Scrape document content
        content_data = scrape_document_content(doc['url'])
        
        if not content_data['content'] or len(content_data['content']) < 100:
            logger.warning(f"Skipping {doc['title']} - insufficient content")
            continue
        
        # Chunk the content
        chunks = chunk_text(content_data['content'])
        logger.info(f"Created {len(chunks)} chunks for {doc['title']}")
        
        # Process each chunk
        points = []
        for i, chunk in enumerate(chunks):
            try:
                # Create embedding
                embedding_response = embed_text(
                    text=chunk,
                    model=config.openai.embeddings.model
                )
                embedding = embedding_response.data[0].embedding
                
                # Create point with proper metadata for ZJN documents
                # Ensure law_name matches what the router expects
                law_name = 'zakon_o_javnim_nabavkama'
                
                # Create a normalized source_collection name that matches router expectations
                source_collection = doc['type']
                if doc['type'] == 'ministar_finansija':
                    source_collection = 'podzakonski_akti_ministra_finansija'
                elif doc['type'] == 'kancelarija':
                    source_collection = 'podzakonski_akti_kancelarija'
                elif doc['type'] == 'vlada':
                    source_collection = 'podzakonski_akti_vlade'
                
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        'title': content_data['title'],
                        'text': chunk,
                        'link': content_data['url'],
                        'law_name': law_name,
                        'source_collection': source_collection,
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'document_type': doc['type'],
                        'original_title': doc['title']  # Keep original title for reference
                    }
                )
                points.append(point)
                
                # Upload in batches
                if len(points) >= 50:
                    client.upsert(
                        collection_name=collection_name,
                        points=points
                    )
                    total_uploaded += len(points)
                    logger.info(f"Uploaded batch of {len(points)} points. Total: {total_uploaded}")
                    points = []
                    time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error processing chunk {i} of {doc['title']}: {e}")
                continue
        
        # Upload remaining points
        if points:
            client.upsert(
                collection_name=collection_name,
                points=points
            )
            total_uploaded += len(points)
            logger.info(f"Uploaded final batch of {len(points)} points. Total: {total_uploaded}")
        
        # Rate limiting between documents
        time.sleep(2)
    
    logger.info(f"Upload complete! Total points uploaded: {total_uploaded}")


def main():
    """Main function to upgrade Qdrant database."""
    logger.info("Starting Qdrant upgrade process...")
    
    # Initialize clients
    qdrant_client = initialize_qdrant()
    config = load_config()
    
    # Scrape document links
    logger.info("Scraping document links from official portal...")
    documents = scrape_document_links(BASE_URL)
    
    if not documents:
        logger.error("No documents found. Please check the website structure.")
        return
    
    # Filter out navigation and non-document links
    excluded_keywords = ['о нама', 'o nama', 'активности', 'aktivnosti', 'контакт', 'kontakt', 
                        'претрага', 'pretraga', 'lat', 'cir', 'ћирилица', 'латиница']
    
    # Filter for actual document links - be more inclusive
    document_keywords = [
        'pravilnik', 'uredba', 'odluka', 'uputstvo', 'izmena', 'dopuna',
        'izmenama', 'dopunama', 'zakon', 'zjn', 'javne nabavke', 'javnim nabavkama',
        'sadržini', 'sadrzini', 'sadržaju', 'sadrzaju', 'načinu', 'nacinu',
        'postupku', 'uslovima', 'kriterijuma', 'kriterijuma', 'registru', 'registar',
        'serifikatu', 'certifikatu', 'monitoringu', 'rečniku', 'recniku', 'obrazaca',
        'izjavi', 'izjavi', 'ugovorima', 'dobara', 'energetskoj', 'efikasnosti',
        'službeni glasnik', 'sluzbeni glasnik', 'glasnik', 'br.', 'broj'
    ]
    
    # Filter documents - include all that look like legal documents
    relevant_docs = [
        doc for doc in documents
        if not any(excluded in doc['title'].lower() for excluded in excluded_keywords)
        and (
            any(keyword in doc['title'].lower() for keyword in document_keywords)
            or doc['type'] in ['vlada', 'kancelarija', 'ministar_finansija', 'zakon']
            or doc['url'].lower().endswith('.pdf')
            or 'službeni glasnik' in doc['title'].lower()
            or 'sluzbeni glasnik' in doc['title'].lower()
            or ('glasnik' in doc['title'].lower() and 'br.' in doc['title'].lower())
        )
        and len(doc['title']) > 5  # Allow shorter titles for document names
    ]
    
    # Prioritize specific document types mentioned by user
    priority_keywords = [
        'pravilnik o sadržini', 'pravilnik o postupku', 'pravilnik o načinu',
        'pravilnik o uslovima', 'pravilnik o kriterijuma', 'pravilnik o registru',
        'pravilnik o sertifikatu', 'pravilnik o monitoringu', 'pravilnik o rečniku',
        'pravilnik o obrazaca', 'uputstvo o načinu', 'uputstvo za korišćenje',
        'izmenama i dopunama zakona', 'uredba o javnim nabavkama', 'odluka o utvrđivanju'
    ]
    
    priority_docs = [
        doc for doc in relevant_docs
        if any(phrase in doc['title'].lower() for phrase in priority_keywords)
    ]
    
    # Also include documents from specific sections
    section_docs = [
        doc for doc in relevant_docs
        if doc['type'] in ['vlada', 'kancelarija', 'ministar_finansija']
    ]
    
    # Combine: priority first, then section docs, then other relevant
    all_relevant = priority_docs + [doc for doc in section_docs if doc not in priority_docs] + [doc for doc in relevant_docs if doc not in priority_docs and doc not in section_docs]
    
    logger.info(f"Found {len(all_relevant)} relevant documents to process")
    logger.info(f"Priority documents: {len(priority_docs)}")
    logger.info(f"Section documents (Vlada/Kancelarija/Ministar): {len(section_docs)}")
    
    # Log some examples
    if all_relevant:
        logger.info("Sample documents to process:")
        for doc in all_relevant[:5]:
            logger.info(f"  - {doc['title']} ({doc['type']})")
    
    if not all_relevant:
        logger.warning("No relevant documents found. Check the website structure.")
        return
    
    # Process and upload
    process_and_upload_documents(
        client=qdrant_client,
        documents=all_relevant,
        config=config
    )
    
    logger.info("Upgrade process completed!")


if __name__ == "__main__":
    main()

