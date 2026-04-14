document
  .getElementById("signin-form")
  .addEventListener("submit", async function (e) {
    e.preventDefault();
    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());

    // 1. Bật SweetAlert2 ở chế độ Loading ngay khi ấn nút
    Swal.fire({
      title: "Đang xử lý...",
      text: "Vui lòng chờ trong giây lát",
      allowOutsideClick: false, // Không cho click ra ngoài để tắt
      didOpen: () => {
        Swal.showLoading();
      },
    });

    try {
      const res = await fetch("/api/signin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      const result = await res.json();

      if (result.success) {
        // 2. Nếu thành công: Đổi sang icon Success và tự động chuyển trang
        Swal.fire({
          icon: "success",
          title: "Đăng nhập thành công!",
          text: "Đang chuyển hướng vào hệ thống...",
          timer: 1500, // Hiện 1.5 giây rồi tự đóng
          showConfirmButton: false, // Ẩn nút OK đi cho mượt
          // Tuỳ biến màu nền cho hợp với giao diện kính mờ của bạn
          background: "rgba(255, 255, 255, 0.95)",
          backdrop: "rgba(0, 0, 0, 0.4)",
        }).then(() => {
          // Hành động này chạy sau khi bảng thông báo đóng lại
          window.location.href = "/";
        });
      } else {
        // 3. Nếu sai tài khoản/pass: Hiện lỗi từ backend
        Swal.fire({
          icon: "error",
          title: "Lỗi đăng nhập",
          text: result.message, // Lấy câu chửi từ backend (ví dụ: "Sai mật khẩu")
          confirmButtonColor: "#06b6d4", // Đổi màu nút OK theo tông màu xanh của bạn
          background: "rgba(255, 255, 255, 0.95)",
        });
      }
    } catch (err) {
      console.error(err);
      // 4. Nếu sập Server hoặc mất mạng internet
      Swal.fire({
        icon: "error",
        title: "Mất kết nối",
        text: "Không thể kết nối đến máy chủ. Vui lòng thử lại sau!",
        confirmButtonColor: "#ef4444",
      });
    }
  });
