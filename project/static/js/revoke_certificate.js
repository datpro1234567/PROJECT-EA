document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("revoke-certificate-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    const confirmed = await Swal.fire({
      title: "Gửi yêu cầu thu hồi?",
      text: "Admin sẽ xem xét và thu hồi chứng chỉ nếu được chấp nhận.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Gửi",
      cancelButtonText: "Hủy",
      confirmButtonColor: "#ef4444",
      cancelButtonColor: "#6b7280",
    }).then((r) => r.isConfirmed);

    if (!confirmed) return;

    Swal.fire({
      title: "Đang gửi...",
      allowOutsideClick: false,
      didOpen: () => Swal.showLoading(),
    });

    try {
      const res = await fetch("/api/user/certificate-requests/revoke", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      const result = await res.json().catch(() => ({}));

      if (res.ok && result.success) {
        await Swal.fire({
          icon: "success",
          title: "Đã gửi yêu cầu",
          text: result.message || "Yêu cầu thu hồi đã được tạo.",
          timer: 1200,
          showConfirmButton: false,
        });
        window.location.href = "/";
        return;
      }

      Swal.fire({
        icon: "error",
        title: "Lỗi",
        text: result.message || "Không thể tạo yêu cầu thu hồi.",
        confirmButtonColor: "#ef4444",
      });
    } catch (err) {
      Swal.fire({
        icon: "error",
        title: "Mất kết nối",
        text: "Không thể kết nối đến máy chủ.",
        confirmButtonColor: "#ef4444",
      });
    }
  });
});
