# backend/utils/mime_types.py
import mimetypes
from enum import Enum

class MimeType(Enum):
    PNG = 'image/png'
    JPEG = 'image/jpeg'
    GIF = 'image/gif'
    BMP = 'image/bmp'
    WEBP = 'image/webp'
    PDF = 'application/pdf'
    DOC = 'application/msword'
    DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    XLS = 'application/vnd.ms-excel'
    XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    PPT = 'application/vnd.ms-powerpoint'
    PPTX = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    TXT = 'text/plain'
    MP3 = 'audio/mpeg'
    WAV = 'audio/wav'
    MP4 = 'video/mp4'
    AVI = 'video/x-msvideo'
    MOV = 'video/quicktime'

class MimeTypeUtil:
    _extension_to_mime = {
        '.png': MimeType.PNG,
        '.jpg': MimeType.JPEG,
        '.jpeg': MimeType.JPEG,
        '.gif': MimeType.GIF,
        '.bmp': MimeType.BMP,
        '.webp': MimeType.WEBP,
        '.pdf': MimeType.PDF,
        '.doc': MimeType.DOC,
        '.docx': MimeType.DOCX,
        '.xls': MimeType.XLS,
        '.xlsx': MimeType.XLSX,
        '.ppt': MimeType.PPT,
        '.pptx': MimeType.PPTX,
        '.txt': MimeType.TXT,
        '.mp3': MimeType.MP3,
        '.wav': MimeType.WAV,
        '.mp4': MimeType.MP4,
        '.avi': MimeType.AVI,
        '.mov': MimeType.MOV
    }

    @classmethod
    def get_mime_type(cls, extension: str) -> str:
        mime_type = cls._extension_to_mime.get(extension.lower())
        if mime_type:
            return mime_type.value
        return mimetypes.types_map.get(extension.lower(), 'application/octet-stream')

    @classmethod
    def get_extension(cls, mime_type: str) -> str:
        for ext, mt in cls._extension_to_mime.items():
            if mt.value == mime_type:
                return ext
        return mimetypes.guess_extension(mime_type) or ''