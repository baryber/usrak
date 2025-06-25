// Auto-generated TypeScript exceptions

export interface ApiException {
    status: number;
    detail: string;
    headers?: string | Record<string, string>;
}

export type ExceptionType = 'UserAlreadyExists' | 'UserAlreadyLoggedIn' | 'UserNotFound' | 'UserDeactivated' | 'UserAlreadyVerified' | 'VerificationFailed' | 'VerificationCodeNotFound' | 'VerificationCodeExpired' | 'VerificationCodeInvalid' | 'UserNotVerified';

export const Exceptions: Record<ExceptionType, ApiException> = {
    UserAlreadyExists: {
        status: 400,
        detail: "User already exists",
        headers: ""
    },
    UserAlreadyLoggedIn: {
        status: 400,
        detail: "Already logged in",
        headers: ""
    },
    UserNotFound: {
        status: 404,
        detail: "User not found",
        headers: ""
    },
    UserDeactivated: {
        status: 403,
        detail: "User deactivated",
        headers: ""
    },
    UserAlreadyVerified: {
        status: 400,
        detail: "Already verified",
        headers: ""
    },
    VerificationFailed: {
        status: 400,
        detail: "Verification failed",
        headers: ""
    },
    VerificationCodeNotFound: {
        status: 404,
        detail: "Code not found",
        headers: ""
    },
    VerificationCodeExpired: {
        status: 400,
        detail: "Code expired",
        headers: ""
    },
    VerificationCodeInvalid: {
        status: 400,
        detail: "Invalid code",
        headers: ""
    },
    UserNotVerified: {
        status: 403,
        detail: "Not verified",
        headers: ""
    }
};
