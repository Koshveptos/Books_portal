import React from 'react';
import { Rating } from './Rating';

interface CommentProps {
  id: number;
  user: {
    id: number;
    username: string;
  };
  rating: number;
  text: string;
  createdAt: string;
  onDelete?: (id: number) => void;
  canDelete?: boolean;
}

export const Comment: React.FC<CommentProps> = ({
  id,
  user,
  rating,
  text,
  createdAt,
  onDelete,
  canDelete = false,
}) => {
  return (
    <div className="bg-white p-4 rounded-lg shadow-md">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span className="font-semibold">{user.username}</span>
          <span className="text-gray-500 text-sm">
            {new Date(createdAt).toLocaleDateString()}
          </span>
        </div>
        {canDelete && onDelete && (
          <button
            onClick={() => onDelete(id)}
            className="text-red-600 hover:text-red-800"
          >
            Удалить
          </button>
        )}
      </div>
      <div className="mb-2">
        <Rating
            value={rating}
            onChange={() => {}}
            disabled
            className="text-sm"
        />
      </div>
      <p className="text-gray-700">{text}</p>
    </div>
  );
};

export default Comment;
