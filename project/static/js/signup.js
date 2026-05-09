document
  .getElementById("signup-form")
  .addEventListener("submit", async function (e) {
    e.preventDefault();
    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());

    Swal.fire({
      title: "Đang xử lý...",
      text: "Vui lòng chờ trong giây lát",
      allowOutsideClick: false,
      didOpen: () => {
        Swal.showLoading();
      },
    });

    try {
      const res = await fetch("/api/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await res.json();
      if (result.success) {
        Swal.fire({
          icon: "success",
          title: "Đăng ký thành công!",
          text: "Bạn có thể đăng nhập ngay bây giờ.",
          timer: 1500,
          showConfirmButton: false,
          background: "rgba(255, 255, 255, 0.95)",
          backdrop: "rgba(0, 0, 0, 0.4)",
        }).then(() => {
          window.location.href = "/signin";
        });
      } else {
        Swal.fire({
          icon: "error",
          title: "Lỗi đăng ký",
          text: result.message,
          confirmButtonColor: "#06b6d4",
          background: "rgba(255, 255, 255, 0.95)",
        });
      }
    } catch (error) {
      console.error("Error:", error);
      Swal.fire({
        icon: "error",
        title: "Lỗi đăng ký",
        text: "Đã xảy ra lỗi khi đăng ký. Vui lòng thử lại.",
        confirmButtonColor: "#06b6d4",
        background: "rgba(255, 255, 255, 0.95)",
      });
    }
  });
