import os
import mimetypes
import uuid

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import ValidationError
import magic


mimetypes.init()


class BaseForm(FlaskForm):
    pass


def HasImageMixin(image_field_name='image'):
    class HasImageMixinImpl:
        def __init__(self, *args, **kwargs):
            self.image_field_data = None
            super().__init__(*args, **kwargs)

        def populate_obj(self, obj):
            old_img = getattr(obj, image_field_name, None)
            super().populate_obj(obj)
            # Reset back to old img - it'll get overwritten if there is a newly uploaded image
            setattr(obj, image_field_name, old_img)
            # Store the file that was validated
            if self.image_field_data:
                # Remove the old image if it exists
                if getattr(obj, image_field_name, None):
                    old_img = os.path.join(current_app.config['DATA_DIRECTORY'], 'images', getattr(obj, image_field_name))
                    if os.path.exists(old_img):
                        os.unlink(old_img)

                mime_data, file, filename = self.image_field_data
                try:
                    with open(os.path.join(current_app.config['DATA_DIRECTORY'], 'images', filename), 'wb') as fp:
                        while True:
                            chunk = mime_data or file.read(8192)
                            if not chunk:
                                break
                            written = 0
                            while written < len(chunk):
                                written += fp.write(chunk[written:])

                            mime_data = None
                    setattr(obj, image_field_name, filename)
                finally:
                    file.close()
                    self.image_field_data = None

    def validate_imfield(form, field):
        file = field.data
        if not file:
            return
        try:
            mime_data = file.read(2048)
            mime = magic.from_buffer(mime_data, mime=True)
            if not mime.startswith('image/'):
                raise ValidationError("The uploaded file is not an image")

            ext = mimetypes.guess_extension(mime)
            if not ext:
                raise ValidationError(f"Can't guess an extension for mime type {mime}")

            form.image_field_data = [
                mime_data,
                file,
                str(uuid.uuid4()) + ext,
            ]
        except:
            file.close()
            raise

    setattr(HasImageMixinImpl, 'validate_' + image_field_name, validate_imfield)
    return HasImageMixinImpl
