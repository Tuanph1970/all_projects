using MediatR;
using AuthService.Application.Common.Exceptions;
using AuthService.Application.Common.Interfaces;
using AuthService.Application.DTOs;

namespace AuthService.Application.Features.Authentication.Queries;

public record GetUserByIdQuery(Guid UserId) : IRequest<UserDto>;

public sealed class GetUserByIdQueryHandler : IRequestHandler<GetUserByIdQuery, UserDto>
{
    private readonly IUnitOfWork _uow;
    public GetUserByIdQueryHandler(IUnitOfWork uow) => _uow = uow;

    public async Task<UserDto> Handle(GetUserByIdQuery request, CancellationToken ct)
    {
        var user = await _uow.Users.GetByIdAsync(request.UserId, ct)
            ?? throw new NotFoundException("User", request.UserId);

        return new UserDto(user.Id, user.Username, user.Email, user.FullName,
            user.Role, user.IsActive, user.CreatedAt, user.LastLoginAt);
    }
}
