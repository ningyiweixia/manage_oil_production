export const PHOTO_ATTACHMENT_ACCEPT = '.jpg,.jpeg,.png,.gif,.webp,.bmp,image/jpeg,image/png,image/gif,image/webp,image/bmp'

export const PHOTO_ATTACHMENT_MIME_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'image/bmp'
])

export const PHOTO_ATTACHMENT_EXTENSIONS = new Set([
  '.jpg',
  '.jpeg',
  '.png',
  '.gif',
  '.webp',
  '.bmp'
])

export const MAX_PHOTO_ATTACHMENT_SIZE = 5 * 1024 * 1024

export function validatePhotoAttachment(file: File): string | null {
  const name = file.name.toLowerCase()
  const extension = name.includes('.') ? name.slice(name.lastIndexOf('.')) : ''
  const typeAllowed = PHOTO_ATTACHMENT_MIME_TYPES.has(file.type)
  const extensionAllowed = PHOTO_ATTACHMENT_EXTENSIONS.has(extension)
  if (!typeAllowed && !extensionAllowed) {
    return '仅支持 JPG、PNG、GIF、WebP、BMP 等常见照片格式'
  }
  if (file.size > MAX_PHOTO_ATTACHMENT_SIZE) {
    return '单张照片不能超过 5MB'
  }
  return null
}

export function readPhotoAttachmentAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('照片读取失败'))
    reader.readAsDataURL(file)
  })
}
