using MediatR;
using AuthService.Application.Common.Exceptions;
using AuthService.Application.Common.Interfaces;
using AuthService.Application.DTOs;

namespace AuthService.Application.Features.Authentication.Queries;

public record GetCurrentUserQuery(Guid UserId) : IRequest<UserDto>;

public sealed class GetCurrentUserQueryHandler : IRequestHandler<GetCurrentUserQuery, UserDto>
{
    private readonly IUnitOfWork _uow;
    public GetCurrentUserQueryHandler(IUnitOfWork uow) => _uow = uow;

    public async Task<UserDto> Handle(GetCurrentUserQuery request, CancellationToken ct)
    {
        var user = await _uow.Users.GetByIdAsync(request.UserId, ct)
            ?? throw new NotFoundException("User", request.UserId);

        return new UserDto(user.Id, user.Username, user.Email, user.FullName,
            user.Role, user.IsActive, user.CreatedAt, user.LastLoginAt);
    }
}
