document.addEventListener("DOMContentLoaded", () => {
  const adminDashboardBtn = document.getElementById("admin-dashboard-btn");
  const generateKeyPairBtn = document.getElementById("generate-root-keypair-btn");
  const generateRootCertBtn = document.getElementById("generate-root-certificate-btn");
  const generateUserKeyPairBtn = document.getElementById("generate-user-keypair-btn");
  const requestCertificateBtn = document.getElementById("request-certificate-btn");
  const viewCertificateRequestsBtn = document.getElementById("view-certificate-requests-btn");
  const revokeCertificateBtn = document.getElementById("revoke-certificate-btn");
  const viewRevocationsBtn = document.getElementById("view-revocations-btn");
  const trackedCertificatesBtn = document.getElementById("tracked-certificates-btn");

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

        const note = document.createElement("div");
        note.style.fontSize = "12px";
        note.style.color = "#6b7280";
        note.style.padding = "6px";
        note.style.backgroundColor = "#f3f4f6";
        note.style.borderRadius = "4px";
        note.style.fontStyle = "italic";
        note.textContent = "ℹ️ Your private key was automatically downloaded when this key pair was generated. It is not stored in the system for security reasons. Keep your private key safe!";

        wrapper.appendChild(title);
        wrapper.appendChild(pub);
        wrapper.appendChild(note);
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
        text: "This action will generate a key pair for signing Root Certificates. The private key will be downloaded immediately.",
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
          const privateKeyPem = result.data?.private_key_pem;
          const keyPairId = result.data?.key_pair_id;

          if (privateKeyPem && keyPairId) {
            const blob = new Blob([privateKeyPem], {
              type: "application/x-pem-file",
            });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `root_private_key_${keyPairId}.pem`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
          }

          Swal.fire({
            icon: "success",
            title: "Success",
            text:
              "Root CA key pair generated successfully. The private key has been downloaded.",
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

  if (trackedCertificatesBtn) {
    trackedCertificatesBtn.addEventListener("click", () => {
      window.location.href = "/certificates/tracked";
    });
  }

  if (generateRootCertBtn) {
    generateRootCertBtn.addEventListener("click", async () => {
      const confirmed = await Swal.fire({
        title: "Create Root Certificate",
        text: "This action will create a self-signed Root Certificate for the entire system. You must upload the Root CA private key file to continue.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Generate",
        cancelButtonText: "Cancel",
        confirmButtonColor: "#10b981",
        cancelButtonColor: "#6b7280",
      }).then((result) => result.isConfirmed);

      if (!confirmed) return;

      const uploadResult = await Swal.fire({
        title: "Upload Root CA Private Key",
        html:
          '<input type="file" id="root-private-key-file" accept=".pem,.key,.txt" class="swal2-file" style="width:100%;" />',
        icon: "info",
        showCancelButton: true,
        confirmButtonText: "Continue",
        cancelButtonText: "Cancel",
        confirmButtonColor: "#10b981",
        cancelButtonColor: "#6b7280",
        focusConfirm: false,
        preConfirm: () => {
          const input = document.getElementById("root-private-key-file");
          const file = input && input.files ? input.files[0] : null;
          if (!file) {
            Swal.showValidationMessage("Please select the Root CA private key file.");
            return false;
          }
          return file;
        },
      });

      if (!uploadResult.isConfirmed) return;

      Swal.fire({
        title: "Generating Root Certificate...",
        text: "Please wait a moment",
        allowOutsideClick: false,
        didOpen: () => {
          Swal.showLoading();
        },
      });

      try {
        const formData = new FormData();
        formData.append("private_key_file", uploadResult.value);

        const res = await fetch("/api/admin/root-certificate", {
          method: "POST",
          body: formData,
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
        text: "This will create a personal public/private key pair linked to your account. Your private key will automatically download - keep it safe!",
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
          // Auto-download the private key
          const privateKeyPem = result.data?.private_key_pem;
          const keyPairId = result.data?.key_pair_id;
          
          if (privateKeyPem && keyPairId) {
            const blob = new Blob([privateKeyPem], { type: "application/x-pem-file" });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `private_key_${keyPairId}.pem`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
          }

          Swal.fire({
            icon: "success",
            title: "Success",
            text:
              "Key pair generated successfully! Your private key has been downloaded. Store it securely.",
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
