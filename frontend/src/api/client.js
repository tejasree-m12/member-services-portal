// One place for every HTTP call to the backend.
//
// Pages never call fetch() directly. They call api.get(...), api.post(...).
// That keeps three things in one spot: the base URL, attaching the login
// token, and turning error responses into one kind of JavaScript error.

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const TOKEN_KEY = "msp_access_token";

export class ApiError extends Error {
  constructor(status, body) {
    const error = (body && body.error) || {};
    super(error.message || "Something went wrong. Please try again.");
    this.status = status;
    this.code = error.code;
    this.details = error.details || {}; // field name -> message, for forms
  }
}

export const tokenStore = {
  get: () => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set: (token) => {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* storage unavailable: the user stays signed in until the tab reloads */
    }
  },
  clear: () => {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* nothing to clear */
    }
  },
};

let memoryToken = tokenStore.get();
let unauthorizedHandler = null;

export function setToken(token) {
  memoryToken = token;
  if (token) tokenStore.set(token);
  else tokenStore.clear();
}

// AuthContext registers a function here so that an expired token signs the
// user out no matter which page made the request.
export function onUnauthorized(handler) {
  unauthorizedHandler = handler;
}

export function buildQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") search.set(key, value);
  });
  const text = search.toString();
  return text ? `?${text}` : "";
}

async function request(method, path, { params, body, formData, asBlob } = {}) {
  const headers = {};
  if (memoryToken) headers.Authorization = `Bearer ${memoryToken}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(BASE_URL + path + buildQuery(params), {
      method,
      headers,
      body: formData || (body !== undefined ? JSON.stringify(body) : undefined),
    });
  } catch {
    throw new ApiError(0, { error: { message: "Cannot reach the server. Check your connection." } });
  }

  if (!response.ok) {
    let errorBody = null;
    try {
      errorBody = await response.json();
    } catch {
      /* the error response was not JSON */
    }
    if (response.status === 401 && path !== "/auth/login" && unauthorizedHandler) {
      unauthorizedHandler();
    }
    throw new ApiError(response.status, errorBody);
  }

  if (asBlob) return response.blob();
  return response.json();
}

export const api = {
  get: (path, params) => request("GET", path, { params }),
  post: (path, body) => request("POST", path, { body: body ?? {} }),
  put: (path, body) => request("PUT", path, { body }),
  patch: (path, body) => request("PATCH", path, { body }),
  delete: (path) => request("DELETE", path),
  upload: (path, file) => {
    const formData = new FormData();
    formData.append("file", file);
    return request("POST", path, { formData });
  },
  // Downloads need the Authorization header, so a plain <a href> will not
  // work. Fetch the file as a blob, then hand it to the browser to save.
  download: async (path, filename, params) => {
    const blob = await request("GET", path, { params, asBlob: true });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};
