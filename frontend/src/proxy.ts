import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

// Chỉ bảo vệ route /chat — landing page vẫn công khai
const isProtectedRoute = createRouteMatcher(['/chat(.*)']);

export default clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Bỏ qua Next.js internals và static files
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
};
