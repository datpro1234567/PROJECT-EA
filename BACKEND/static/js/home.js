document.addEventListener("DOMContentLoaded", () => {
  const adminDashboardBtn = document.getElementById("admin-dashboard-btn");
  const generateKeyPairBtn = document.getElementById("generate-root-keypair-btn");
  const generateRootCertBtn = document.getElementById("generate-root-certificate-btn");
  const generateUserKeyPairBtn = document.getElementById("generate-user-keypair-btn");
  const requestCertificateBtn = document.getElementById("request-certificate-btn");
  const viewCertificateRequestsBtn = document.getElementById("view-certificate-requests-btn");
  const revokeCertificateBtn = document.getElementById("revoke-certificate-btn");
  const viewRevocationsBtn = document.getElementById("view-revocations-btn");

  const userKeypairsList = document.getElementById("user-keypairs-list");
  const userCertificatesList = document.getElementById("user-certificates-list");

  const changePasswordForm = document.getElementById("change-password-form");

  if (adminDashboardBtn) {
    adminDashboardBtn.addEventListener("click", () => {
      window.location.href = "/admin/dashboard";
    });
  }

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
        const canDownloadPrivateKey = Boolean(key.can_download_private_key);

        downloadBtn.textContent = canDownloadPrivateKey
          ? "Download Private Key"
          : "Đã tải";

        downloadBtn.disabled = !canDownloadPrivateKey;
        downloadBtn.style.padding = "4px 10px";
        downloadBtn.style.fontSize = "12px";
        downloadBtn.style.cursor = canDownloadPrivateKey ? "pointer" : "not-allowed";
        downloadBtn.style.opacity = canDownloadPrivateKey ? "1" : "0.6";
        downloadBtn.addEventListener("click", async () => {
          if (downloadBtn.disabled) return;

          downloadBtn.disabled = true;
          downloadBtn.style.cursor = "not-allowed";
          downloadBtn.style.opacity = "0.6";

          try {
            const res = await fetch(`/api/user/keypairs/${key.id}/private`, {
              method: "GET",
              headers: {
                "Accept": "application/x-pem-file,application/json",
              },
            });

            if (!res.ok) {
              const err = await res.json().catch(() => ({}));
              const errorCode = err.error || "";

              if (res.status === 410 || errorCode === "already_downloaded") {
                downloadBtn.textContent = "Đã tải";
                return;
              }

              // Other errors: allow retry
              downloadBtn.disabled = false;
              downloadBtn.style.cursor = "pointer";
              downloadBtn.style.opacity = "1";
              return;
            }

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `private_key_${key.id}.pem`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

            downloadBtn.textContent = "Đã tải";
          } catch (error) {
            console.error("Error downloading private key:", error);
            downloadBtn.disabled = false;
            downloadBtn.style.cursor = "pointer";
            downloadBtn.style.opacity = "1";
          }
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

  async function loadUserCertificates() {
    if (!userCertificatesList) return;

    userCertificatesList.textContent = "Loading...";

    try {
      const res = await fetch("/api/user/certificates", {
        method: "GET",
        headers: {
          "Accept": "application/json",
        },
      });

      const result = await res.json().catch(() => ({}));

      if (!res.ok || !result.success) {
        userCertificatesList.textContent =
          result.message || "Could not load your certificates.";
        return;
      }

      const certs = result.certificates || [];
      if (certs.length === 0) {
        userCertificatesList.textContent = "You do not have any certificates yet.";
        return;
      }

      userCertificatesList.textContent = "";

      certs.forEach((cert) => {
        const wrapper = document.createElement("div");
        wrapper.style.border = "1px solid #e5e7eb";
        wrapper.style.borderRadius = "6px";
        wrapper.style.padding = "8px";
        wrapper.style.marginBottom = "8px";

        const title = document.createElement("div");
        title.style.fontWeight = "600";
        title.style.marginBottom = "4px";
        const statusText = cert.status ? ` (${cert.status})` : "";
        const domainText = cert.domain_name ? ` - ${cert.domain_name}` : "";
        title.textContent = `Cert ID ${cert.certificate_id}${statusText}${domainText}`;

        const meta = document.createElement("div");
        meta.style.fontSize = "12px";
        meta.style.color = "#6b7280";
        const from = cert.valid_from || "";
        const to = cert.valid_to || "";
        meta.textContent = from && to ? `Valid: ${from} → ${to}` : "";

        const downloadBtn = document.createElement("button");
        downloadBtn.type = "button";
        downloadBtn.textContent = "Download Certificate";
        downloadBtn.style.padding = "4px 10px";
        downloadBtn.style.fontSize = "12px";
        downloadBtn.style.cursor = "pointer";
        downloadBtn.addEventListener("click", async () => {
          downloadBtn.disabled = true;
          downloadBtn.style.cursor = "not-allowed";
          downloadBtn.style.opacity = "0.7";

          try {
            const res = await fetch(
              `/api/user/certificates/${cert.certificate_id}/download`,
              {
                method: "GET",
                headers: {
                  "Accept": "application/x-pem-file,application/json",
                },
              }
            );

            if (!res.ok) {
              const err = await res.json().catch(() => ({}));
              Swal.fire({
                icon: "error",
                title: "Error",
                text: err.message || "Could not download certificate.",
                confirmButtonColor: "#ef4444",
              });
              downloadBtn.disabled = false;
              downloadBtn.style.cursor = "pointer";
              downloadBtn.style.opacity = "1";
              return;
            }

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `certificate_${cert.certificate_id}.pem`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

            downloadBtn.disabled = false;
            downloadBtn.style.cursor = "pointer";
            downloadBtn.style.opacity = "1";
          } catch (error) {
            console.error("Error downloading certificate:", error);
            downloadBtn.disabled = false;
            downloadBtn.style.cursor = "pointer";
            downloadBtn.style.opacity = "1";
          }
        });

        wrapper.appendChild(title);
        if (meta.textContent) wrapper.appendChild(meta);
        wrapper.appendChild(downloadBtn);
        userCertificatesList.appendChild(wrapper);
      });
    } catch (error) {
      console.error("Error loading user certificates:", error);
      userCertificatesList.textContent =
        "Error while loading certificates. Please try again later.";
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

  if (requestCertificateBtn) {
    requestCertificateBtn.addEventListener("click", () => {
      window.location.href = "/certificate/request";
    });
  }

  if (revokeCertificateBtn) {
    revokeCertificateBtn.addEventListener("click", () => {
      window.location.href = "/certificate/revoke";
    });
  }

  if (viewCertificateRequestsBtn) {
    viewCertificateRequestsBtn.addEventListener("click", () => {
      window.location.href = "/admin/certificate-requests";
    });
  }

  if (viewRevocationsBtn) {
    viewRevocationsBtn.addEventListener("click", () => {
      window.location.href = "/revocations";
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
  loadUserCertificates();
});
