document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("certificate-request-form");
  if (!form) return;

  const csrOut = document.getElementById("csr_pem");
  const subjectC = document.getElementById("subject_c");

  subjectC?.addEventListener("input", () => {
    subjectC.value = (subjectC.value || "").toUpperCase();
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData(form);

    Swal.fire({
      title: "Đang xử lý...",
      text: "Vui lòng chờ trong giây lát",
      allowOutsideClick: false,
      didOpen: () => {
        Swal.showLoading();
      },
    });

    try {
      const res = await fetch("/api/user/certificate-requests/issue", {
        method: "POST",
        body: formData,
      });

      const result = await res.json().catch(() => ({}));

      if (res.ok && result.success) {
        const csr = result?.data?.csr_pem;
        if (csrOut && typeof csr === "string") {
          csrOut.value = csr;
        }

        Swal.fire({
          icon: "success",
          title: "Đã gửi yêu cầu",
          text: result.message || "Yêu cầu đã được tạo.",
          timer: 1500,
          showConfirmButton: false,
          background: "rgba(255, 255, 255, 0.95)",
          backdrop: "rgba(0, 0, 0, 0.4)",
        });
        return;
      }

      Swal.fire({
        icon: "error",
        title: "Lỗi",
        text: result.message || "Không thể tạo yêu cầu. Vui lòng thử lại.",
        confirmButtonColor: "#06b6d4",
        background: "rgba(255, 255, 255, 0.95)",
      });
    } catch (error) {
      console.error("Error:", error);
      Swal.fire({
        icon: "error",
        title: "Mất kết nối",
        text: "Không thể kết nối đến máy chủ. Vui lòng thử lại sau!",
        confirmButtonColor: "#ef4444",
      });
    }
  });
});
