"""
Document upload and management routes.
Scoped under /v1/programs/{program_id}/documents
"""
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from beacon.auth.dependencies import CurrentUser
from beacon.core.database import DbSession

router = APIRouter()

ALLOWED_MIME_TYPES = {"application/pdf"}
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


@router.get("", response_model=list[dict])
async def list_documents(
    program_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
):
    """List all documents uploaded for a program."""
    from beacon.services.document_ingestion import DocumentIngestionService
    svc = DocumentIngestionService(session)
    return await svc.list_documents(str(program_id))


@router.post("", response_model=dict, status_code=201)
async def upload_document(
    program_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    category: str = Query(default="general"),
    description: str = Query(default=None),
):
    """
    Upload a PDF document for a program.
    The document is parsed, chunked, and embedded automatically.
    Large documents may take 30-60 seconds to process.
    """
    # Validate file type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Only PDF files are supported. Got: {file.content_type}",
        )

    # Read file
    file_bytes = await file.read()

    # Validate file size
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB.",
        )

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Generate safe filename
    safe_filename = f"{uuid.uuid4()}.pdf"

    from beacon.services.document_ingestion import DocumentIngestionService
    svc = DocumentIngestionService(session)

    result = await svc.ingest_pdf(
        program_id=str(program_id),
        filename=safe_filename,
        original_filename=file.filename or "document.pdf",
        file_bytes=file_bytes,
        category=category,
        description=description,
        uploaded_by_id=str(current_user.id) if current_user else None,
    )

    await session.commit()
    return result


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    program_id: uuid.UUID,
    document_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
):
    """Delete a document and all its chunks."""
    from beacon.services.document_ingestion import DocumentIngestionService
    svc = DocumentIngestionService(session)
    await svc.delete_document(str(document_id))
    await session.commit()
