import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { User } from '../types/user';

const ProfilePage: React.FC = () => {
  const { user, isLoading, error } = useAuth();
  const [profileData, setProfileData] = useState<User | null>(null);

  useEffect(() => {
    if (user) {
      setProfileData(user);
    }
  }, [user]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-red-500 text-xl">{error}</div>
      </div>
    );
  }

  if (!profileData) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-gray-500 text-xl">Пользователь не найден</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Профиль пользователя</h1>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Email
              </label>
              <p className="mt-1 text-lg text-gray-900">{profileData.email}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Роль
              </label>
              <p className="mt-1 text-lg text-gray-900">{profileData.role}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Дата регистрации
              </label>
              <p className="mt-1 text-lg text-gray-900">
                {new Date(profileData.created_at).toLocaleDateString()}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Последнее обновление
              </label>
              <p className="mt-1 text-lg text-gray-900">
                {new Date(profileData.updated_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
