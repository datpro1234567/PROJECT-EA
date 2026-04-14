document.addEventListener("DOMContentLoaded", () => {
  const generateBtn = document.getElementById("generate-root-keypair-btn");

  if (!generateBtn) return;

  generateBtn.addEventListener("click", async () => {
    const confirmed = await Swal.fire({
      title: "Generate Root Key Pair",
      text: "This action will generate a key pair for signing Root Certificates.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Generate",
      cancelButtonText: "Cancel",
      confirmButtonColor: "#06b6d4",
      cancelButtonColor: "#6b7280",
    }).then((result) => result.isConfirmed);

    if (!confirmed) return;

    Swal.fire({
      title: "Generating Root Key Pair...",
      text: "Please wait a moment",
      allowOutsideClick: false,
      didOpen: () => {
        Swal.showLoading();
      },
    });

    try {
      const res = await fetch("/api/admin/root-keypair", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
      });

      const result = await res.json().catch(() => ({}));

      if (res.ok && result.success) {
        Swal.fire({
          icon: "success",
          title: "Success",
          text: result.message || "Successfully generated Root CA key pair.",
          confirmButtonColor: "#06b6d4",
        });
      } else if (res.status === 403) {
        Swal.fire({
          icon: "error",
          title: "No Permission",
          text:
            result.message ||
            "You do not have permission to perform this action.",
          confirmButtonColor: "#ef4444",
        });
      } else {
        Swal.fire({
          icon: "error",
          title: "Error",
          text:
            result.message ||
            "Cannot generate Root CA key pair. Please try again.",
          confirmButtonColor: "#ef4444",
        });
      }
    } catch (error) {
      console.error("Error generating root key pair:", error);
      Swal.fire({
        icon: "error",
        title: "Error",
        text: "Cannot connect to the server. Please try again later.",
        confirmButtonColor: "#ef4444",
      });
    }
  });
});
