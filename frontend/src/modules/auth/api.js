function extractErrorMessage(data, fallback) {
  if (data && typeof data === "object" && typeof data.detail === "string" && data.detail.trim()) {
    return data.detail;
  }
  return fallback;
}

export async function requestRegisterCode(payload) {
  const response = await fetch("/api/v1/auth/register/request-code", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "request register code failed"));
  }
  return data;
}

export async function registerRequest(payload) {
  const response = await fetch("/api/v1/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "register failed"));
  }
  return data;
}

export async function loginRequest(payload) {
  const loginResponse = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!loginResponse.ok) {
    throw new Error("login failed");
  }

  const loginData = await loginResponse.json();
  const meResponse = await fetch("/api/v1/auth/me", {
    method: "GET",
    headers: { Authorization: `Bearer ${loginData.access_token}` }
  });

  if (!meResponse.ok) {
    throw new Error("load profile failed");
  }

  const meData = await meResponse.json();

  return {
    access_token: loginData.access_token,
    refresh_token: loginData.refresh_token,
    role: meData.role,
    email: meData.email,
    display_name: meData.display_name
  };
}
