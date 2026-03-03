import { handleUnauthorizedResponse } from "../auth/session";

export function getAccessToken() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem("wakou_access_token") || "";
}

function authHeaders() {
  const token = getAccessToken();
  return { Authorization: `Bearer ${token}` };
}

export async function fetchCommRoom(roomId) {
  const response = await fetch(`/api/v1/comm-rooms/${roomId}`, {
    method: "GET",
    headers: authHeaders()
  });
  if (!response.ok) {
    if (handleUnauthorizedResponse(response)) {
      throw new Error("login required");
    }
    throw new Error("load comm room failed");
  }
  return response.json();
}

export async function sendMessage(roomId, payload) {
  const response = await fetch(`/api/v1/comm-rooms/${roomId}/messages`, {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    if (handleUnauthorizedResponse(response)) {
      throw new Error("login required");
    }
    throw new Error("send message failed");
  }
  return response.json();
}

export async function submitFinalQuote(roomId, payload) {
  const response = await fetch(`/api/v1/comm-rooms/${roomId}/final-quote`, {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    if (handleUnauthorizedResponse(response)) {
      throw new Error("login required");
    }
    throw new Error("submit quote failed");
  }
  return response.json();
}

export async function acceptQuote(roomId) {
  const response = await fetch(`/api/v1/comm-rooms/${roomId}/accept-quote`, {
    method: "POST",
    headers: authHeaders()
  });
  if (!response.ok) {
    if (handleUnauthorizedResponse(response)) {
      throw new Error("login required");
    }
    throw new Error("accept quote failed");
  }
  return response.json();
}

export async function uploadTransferProof(roomId, payload) {
  const response = await fetch(`/api/v1/comm-rooms/${roomId}/upload-proof`, {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    if (handleUnauthorizedResponse(response)) {
      throw new Error("login required");
    }
    throw new Error("upload proof failed");
  }
  return response.json();
}

export async function uploadTransferProofFile(roomId, file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`/api/v1/comm-rooms/${roomId}/upload-proof-file`, {
    method: "POST",
    headers: authHeaders(),
    body: formData
  });
  if (!response.ok) {
    if (handleUnauthorizedResponse(response)) {
      throw new Error("login required");
    }
    throw new Error("upload proof file failed");
  }
  return response.json();
}

export async function confirmPayment(orderId) {
  const response = await fetch(`/api/v1/orders/${orderId}/confirm-payment`, {
    method: "POST",
    headers: authHeaders()
  });
  if (!response.ok) {
    if (handleUnauthorizedResponse(response)) {
      throw new Error("login required");
    }
    throw new Error("confirm payment failed");
  }
  return response.json();
}
