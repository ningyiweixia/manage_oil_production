from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]


class PhotoAttachmentContractTest(unittest.TestCase):
    def test_approval_form_accepts_common_photo_formats(self):
        view = (REPO_ROOT / "frontend/src/views/ApprovalWorkbench.vue").read_text(encoding="utf-8")

        self.assertIn('accept=".jpg,.jpeg,.png,.gif,.webp,.bmp,image/jpeg,image/png,image/gif,image/webp,image/bmp"', view)

    def test_photo_attachment_utility_validates_type_and_size(self):
        util = (REPO_ROOT / "frontend/src/utils/photoAttachments.ts").read_text(encoding="utf-8")

        for mime in ("image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"):
            self.assertIn(mime, util)
        for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
            self.assertIn(ext, util)
        self.assertIn("MAX_PHOTO_ATTACHMENT_SIZE", util)
        self.assertIn("validatePhotoAttachment", util)
        self.assertIn("readPhotoAttachmentAsDataUrl", util)


if __name__ == "__main__":
    unittest.main()
