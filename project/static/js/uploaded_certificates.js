document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('upload-cert-form');
  const fileInput = document.getElementById('certificate_file');

  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const file = fileInput?.files?.[0];
    if (!file) {
      Swal.fire({
        icon: 'error',
        title: 'Thiếu file',
        text: 'Vui lòng chọn file chứng nhận.',
        confirmButtonColor: '#ef4444'
      });
      return;
    }

    const fd = new FormData();
    fd.append('certificate_file', file);

    Swal.fire({
      title: 'Đang upload...',
      text: 'Vui lòng chờ',
      allowOutsideClick: false,
      didOpen: () => Swal.showLoading()
    });

    try {
      const res = await fetch('/api/user/uploaded-certificates', {
        method: 'POST',
        body: fd
      });

      const result = await res.json().catch(() => ({}));
      if (!res.ok || !result.success) {
        throw new Error(result.message || 'Upload failed.');
      }

      await Swal.fire({
        icon: 'success',
        title: 'Thành công',
        text: result.message || 'Đã lưu chứng nhận để theo dõi.',
        confirmButtonColor: '#10b981'
      });

      window.location.reload();
    } catch (err) {
      Swal.fire({
        icon: 'error',
        title: 'Lỗi',
        text: String(err?.message || err),
        confirmButtonColor: '#ef4444'
      });
    }
  });
});
