import { ProtectedRoute } from "../../features/auth/components/ProtectedRoute";
import { ProfileForm } from "../../features/profile/components/ProfileForm";

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <ProfileForm />
    </ProtectedRoute>
  );
}
