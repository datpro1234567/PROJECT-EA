document.addEventListener("DOMContentLoaded", () => {
  const generateKeyPairBtn = document.getElementById("generate-root-keypair-btn");
  const generateRootCertBtn = document.getElementById("generate-root-certificate-btn");
  const generateUserKeyPairBtn = document.getElementById("generate-user-keypair-btn");

  const userKeypairsList = document.getElementById("user-keypairs-list");

  const changePasswordForm = document.getElementById("change-password-form");

  async function loadUserKeyPairs() {
    if (!userKeypairsList) return;

    userKeypairsList.textContent = "Loading...";

    try {
      const res = await fetch("/api/user/keypairs", {
        method: "GET",
        headers: {
          "Accept": "application/json",
        },
      });

      const result = await res.json().catch(() => ({}));

      if (!res.ok || !result.success) {
        userKeypairsList.textContent =
          result.message || "Could not load your key pairs.";
        return;
      }

      const keys = result.keys || [];
      if (keys.length === 0) {
        userKeypairsList.textContent = "You do not have any key pairs yet.";
        return;
      }

      userKeypairsList.textContent = "";

      keys.forEach((key) => {
        const wrapper = document.createElement("div");
        wrapper.style.border = "1px solid #e5e7eb";
        wrapper.style.borderRadius = "6px";
        wrapper.style.padding = "8px";
        wrapper.style.marginBottom = "8px";

        const title = document.createElement("div");
        title.style.fontWeight = "600";
        title.style.marginBottom = "4px";
        title.textContent = `ID ${key.id} - ${key.algorithm} ${key.key_size} (${key.status})`;

        const pub = document.createElement("textarea");
        pub.readOnly = true;
        pub.rows = 4;
        pub.style.width = "100%";
        pub.style.fontSize = "12px";
        pub.style.fontFamily = "monospace";
        pub.style.marginBottom = "6px";
        pub.value = key.public_key || "";

        const downloadBtn = document.createElement("button");
        downloadBtn.type = "button";
        downloadBtn.textContent = "Download Private Key";
        downloadBtn.style.padding = "4px 10px";
        downloadBtn.style.fontSize = "12px";
        downloadBtn.style.cursor = "pointer";
        downloadBtn.addEventListener("click", () => {
          window.location.href = `/api/user/keypairs/${key.id}/private`;
        });

        wrapper.appendChild(title);
        wrapper.appendChild(pub);
        wrapper.appendChild(downloadBtn);
        userKeypairsList.appendChild(wrapper);
      });
    } catch (error) {
      console.error("Error loading user key pairs:", error);
      userKeypairsList.textContent =
        "Error while loading key pairs. Please try again later.";
    }
  }

  if (generateKeyPairBtn) {
    generateKeyPairBtn.addEventListener("click", async () => {
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
  }

  if (generateRootCertBtn) {
    generateRootCertBtn.addEventListener("click", async () => {
      const confirmed = await Swal.fire({
        title: "Create Root Certificate",
        text: "This action will create a self-signed Root Certificate for the entire system.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Generate",
        cancelButtonText: "Cancel",
        confirmButtonColor: "#10b981",
        cancelButtonColor: "#6b7280",
      }).then((result) => result.isConfirmed);

      if (!confirmed) return;

      Swal.fire({
        title: "Generating Root Certificate...",
        text: "Please wait a moment",
        allowOutsideClick: false,
        didOpen: () => {
          Swal.showLoading();
        },
      });

      try {
        const res = await fetch("/api/admin/root-certificate", {
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
            text:
              result.message ||
              "Successfully generated Root CA Certificate for the system.",
            confirmButtonColor: "#10b981",
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
              "Cannot generate Root Certificate. Please try again.",
            confirmButtonColor: "#ef4444",
          });
        }
      } catch (error) {
        console.error("Error generating root certificate:", error);
        Swal.fire({
          icon: "error",
          title: "Error",
          text: "Cannot connect to the server. Please try again later.",
          confirmButtonColor: "#ef4444",
        });
      }
    });
  }

  if (generateUserKeyPairBtn) {
    generateUserKeyPairBtn.addEventListener("click", async () => {
      const confirmed = await Swal.fire({
        title: "Generate Your Key Pair",
        text: "This will create a personal public/private key pair linked to your account.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Generate",
        cancelButtonText: "Cancel",
        confirmButtonColor: "#06b6d4",
        cancelButtonColor: "#6b7280",
      }).then((result) => result.isConfirmed);

      if (!confirmed) return;

      Swal.fire({
        title: "Generating Key Pair...",
        text: "Please wait a moment",
        allowOutsideClick: false,
        didOpen: () => {
          Swal.showLoading();
        },
      });

      try {
        const res = await fetch("/api/user/keypair", {
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
            text:
              result.message ||
              "Successfully generated your personal key pair.",
            confirmButtonColor: "#06b6d4",
          }).then(() => {
            loadUserKeyPairs();
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
              "Cannot generate your key pair. Please try again.",
            confirmButtonColor: "#ef4444",
          });
        }
      } catch (error) {
        console.error("Error generating user key pair:", error);
        Swal.fire({
          icon: "error",
          title: "Error",
          text: "Cannot connect to the server. Please try again later.",
          confirmButtonColor: "#ef4444",
        });
      }
    });
  }

  if (changePasswordForm) {
    changePasswordForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const formData = new FormData(changePasswordForm);
      const data = Object.fromEntries(formData.entries());

      Swal.fire({
        title: "Updating password...",
        text: "Please wait a moment",
        allowOutsideClick: false,
        didOpen: () => {
          Swal.showLoading();
        },
      });

      try {
        const res = await fetch("/api/change-password", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(data),
        });

        const result = await res.json().catch(() => ({}));

        if (res.ok && result.success) {
          Swal.fire({
            icon: "success",
            title: "Password updated",
            text:
              result.message ||
              "Your password has been changed successfully.",
            confirmButtonColor: "#06b6d4",
          }).then(() => {
            changePasswordForm.reset();
          });
        } else {
          Swal.fire({
            icon: "error",
            title: "Error",
            text:
              result.message ||
              "Could not change your password. Please check your input and try again.",
            confirmButtonColor: "#ef4444",
          });
        }
      } catch (error) {
        console.error("Error changing password:", error);
        Swal.fire({
          icon: "error",
          title: "Error",
          text: "Cannot connect to the server. Please try again later.",
          confirmButtonColor: "#ef4444",
        });
      }
    });
  }

  // Initial load of user key pairs if section is present
  loadUserKeyPairs();
});
